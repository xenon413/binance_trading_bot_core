from decimal import Decimal, ROUND_DOWN, ROUND_UP
import time
import pandas as pd
from abc import ABC, abstractmethod
import json
import sys

from core import (
    PositionSide, OrderSide, MarginType, Base, BotMode, LogLevel,
    LogHandle, BotAction, BotError, CandleInterval, BinanceError,
    APIManager, OrderType, log_lifecycle, set_min_process_time
)
from core.schema.bot_schema import EngineSettings, StratSettings, SignalSettings, DFEntry, TradingBotKwargs

# from .signal_handle import SignalHandle
from .signal_handle import SignalHandle
from core.schema.schema import OpenOrder, SignalStatus, CloseOrder, Event, ExecuteOrder

from .strat.base import Strat

CRITICAL = True

# create a base api for engine
class BaseEngine:
    def __init__(self, settings:TradingBotKwargs):
        self.settings = settings

        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)
        self._log_handle.write_log(f"bot mode: {self.settings.engine_settings.mode}", LogLevel.INFO)
        
        ### should also try to use the target, kwargs way???
        ### because currently only one signal handle and no other so keep 
        self.signal_handle = SignalHandle(self.settings.signal_settings)
        self.strat_handle:Strat = self.settings.strat_settings.create_instance()

        # init var
        self.engine = None

    @log_lifecycle
    def step(self)->bool:
        row = self.get_row()

        # if no next row
        if row is None:
            return False
        
        stat = self.strat_handle.update(row)
        self.action(stat)
        return True
    
    @abstractmethod
    def get_row(self)->pd.Series|None:...

    @abstractmethod
    def action(self, stat:SignalStatus)->None:...

    ### helper method might move outside of class to helper.py later on
    @staticmethod
    def floor_step(qty:float|Decimal|str, step_size:float|Decimal|str)->Decimal:
        if step_size <= 0:
            raise BotError("step_size must be a positive number", BotAction.EXIT)
        
        qty:Decimal = Decimal(str(qty))
        step = Decimal(str(step_size))
        return (qty/step).quantize(Decimal("1"), rounding=ROUND_DOWN)*step

    @staticmethod
    def ceil_step(qty:float|Decimal|str, step_size:float|Decimal|str)->Decimal:
        if step_size <= 0:
            raise BotError("step_size must be a positive number", BotAction.EXIT)
        
        qty = Decimal(str(qty))
        step = Decimal(str(step_size))
        return (qty/step).quantize(Decimal("1"), rounding=ROUND_UP)*step
    
# all strat needs to be able to handle one kline data at a time 
# if return from strat all engine must wait till the next base kline
class RecordEngine(BaseEngine):
    '''handle mode: RECORD'''
    def __init__(self, settings:TradingBotKwargs):
        super().__init__(settings)

        test = True if settings.engine_settings.mode == BotMode.TEST_TRADE else False
        self.api_manager = APIManager(test, settings.signal_settings)

        #TODO: move to DFConfig
        self.df_entry:dict[str, DFEntry] = {"main": settings.signal_settings.df_config.main}
        if settings.signal_settings.df_config.others:
            self.df_entry |= settings.signal_settings.df_config.others
            
        #TODO: also move to DFConfig
        self.min_interval = min(self.df_entry.values(), key=lambda x:x.interval.seconds).interval

    def wait(self, klines:int, interval:CandleInterval):
        cur_time = int(time.time())
        # +1 just in case binance update lag
        time.sleep(interval.seconds - cur_time%interval.seconds + (klines-1)*interval.seconds + 1)
        self.log_event(
            Event(
                time=cur_time,
                info={"wait":f"from {cur_time} to {int(time.time())}"}
            )
        )

    # NOTE: max request speed for normal endpoint request is 0.25s 
    # and for order is 0.5s, min process time set to 0.6s for safty
    # (temporary till websocket is fixed)
    # (websocket update speed is 0.25s)
    @log_lifecycle
    @set_min_process_time(0.6) 
    def get_row(self):
        # is df miss match still a issue after using signal handle v2?
        # TODO: this is cooked we need to async this shit
        # potential kline miss aline when getting dfs
        dfs = {k:self.api_manager.get_cont_kline_df(v.symbol, v.interval) for k, v in self.df_entry.items()}

        # TODO: need a layer to garenteen data integrety
        meta_df = self.signal_handle.config_signal(dfs)
        meta_dict = meta_df.reset_index().to_dict("records")

        return meta_dict[-1]

    def action(self, stat:SignalStatus):
        # record event
        if stat.event:
            self.log_event(stat.event)

        if stat.wait > 0:
            self.wait(stat.wait, self.min_interval)

    def log_event(self, event:Event)->None:
        with open("trades.jsonl", "a") as f:
            f.write(event.to_jsons() + "\n")

class LiveEngine(RecordEngine):
    '''handle mode: LIVE_TRADING, TEST_TRADING'''
    def __init__(self, settings:TradingBotKwargs):
        super().__init__(settings)

        # init
        self.__base = None
        self.__quote = None
        self.__leverage = None
        self.__margin_type = None
        self.__symbol_info = None
        self.__multi_assets_margin = None
        self.__dual_side_position = None

        # load settings / warm up
        self.dual_side_position = self.settings.engine_settings.dual_side_position
        self.multi_assets_margin = self.settings.engine_settings.multi_assets_margin
        self.margin_type = self.settings.engine_settings.margin_type
        self.drag_order_threash = self.settings.engine_settings.drag_order_threash
        self.max_reorder = self.settings.engine_settings.max_reorder
        self.margin_buffer = self.settings.engine_settings.margin_buffer

    @log_lifecycle
    def action(self, stat:SignalStatus):
        # record event
        if stat.event:
            self.log_event(stat.event)

        # execute order
        if isinstance(stat.event, OpenOrder):
            max_qty = min(self.total_quote_asset_balance, self.settings.engine_settings.margin_limit[1])
            if self.available_quote_asset_balance < self.settings.engine_settings.margin_limit[0]:
                raise BotError("available margin lower than low margin limit", BotAction.EXIT)
            
            ### also modularize the request method into settings
            res = self.api_manager.drag_order(
                self.settings.engine_settings.symbol,
                stat.event.order_side,
                stat.event.position_side,
                self.quote_asset2order_size(max_qty*stat.event.margin_pct),
                auto_cancel=180000 ### temp solution modularize later 
            )
            
            # if faild to order
            if res.filled_qty == 0:
                res.is_final = True
                # log
                self.log_event(res)

                # restart strat
                self.strat_handle.reset()

            else:
                self.log_event(res)
                
        elif isinstance(stat.event, CloseOrder):
            res = self.api_manager.get_position_info(self.settings.engine_settings.symbol)
            position = res.get_position(self.settings.engine_settings.symbol, stat.event.position_side)
            if position is None:
                raise BotError("trying to close empty position", BotAction.EXIT)
            
            res = self.api_manager.drag_order(
                self.settings.engine_settings.symbol,
                stat.event.order_side,
                stat.event.position_side,
                abs(position.position_amt)*stat.event.position_pct
            )

            self.log_event(res)
            # if faild to order(impossible in theory)
            if res.filled_qty == 0:
                raise BotError("failed to close order", BotAction.EXIT)
                
        ### need to count before order palcement
        if stat.wait > 0:
            self.wait(stat.wait, self.min_interval)

    @log_lifecycle
    def update_symbol_config(self):
        '''
        update include:
            leverage
            margin type
        '''
        symbol_config = self.api_manager.get_symbol_config(self.settings.engine_settings.symbol)
        self.__leverage = symbol_config[0].leverage
        self.__margin_type = symbol_config[0].margin_type

    @log_lifecycle
    def update_accout_config(self):
        '''
        update include:
            dual side position
            multi assets margin
        '''
        account_config = self.api_manager.get_account_config()
        self.__dual_side_position = account_config.dual_side_position
        self.__multi_assets_margin = account_config.multi_assets_margin

        if account_config.can_trade == False:
            raise BotError("account setting: canTrade=False", BotAction.EXIT)

    @log_lifecycle
    def update_exchange_info(self):
        '''
        update include:
            base/quote asset
            symbol info
        '''
        # get exchange info
        info = self.api_manager.get_exchange_info()
        info = info.symbols

        # get symbol info
        for i in info:
            if i.symbol == self.settings.engine_settings.symbol:
                info = i
                break
        else:
            raise BotError("no matched symbol in exchange info", BotAction.EXIT)
         
        # check if trading
        if info.status != "TRADING":
            raise BotError(f"symbol status={info.status}", BotAction.EXIT)
        
        # set base/quote asset
        self.__base = info.baseAsset
        self.__quote = info.quoteAsset

        # get symbol info
        info = info.filters

        ### change symbol info to basemodel or typedictlater
        self.__symbol_info = {
            "tick_size":None, # price step
            "limit_max_qty":None, # limit order 
            "limit_min_qty":None,
            "limit_step_size":None, # qty step size
            "market_max_qty":None, # market order
            "market_min_qty":None,
            "market_step_size":None,
            "max_order_num":None, # max order at the same time
            "min_notional":None # price*quantity
        }
        for i in info:
            if i.filter_type == "PRICE_FILTER":
                self.__symbol_info["tick_size"] = i.tick_size

            elif i.filter_type == "LOT_SIZE":
                self.__symbol_info["limit_max_qty"] = i.max_qty
                self.__symbol_info["limit_min_qty"] = i.min_qty
                self.__symbol_info["limit_step_size"] = i.step_size

            elif i.filter_type == "MARKET_LOT_SIZE":
                self.__symbol_info["market_max_qty"] = i.max_qty
                self.__symbol_info["market_min_qty"] = i.min_qty
                self.__symbol_info["market_step_size"] = i.step_size

            elif i.filter_type == "MAX_NUM_ORDERS":
                self.__symbol_info["max_order_num"]  = i.limit

            elif i.filter_type == "MIN_NOTIONAL":
                self.__symbol_info["min_notional"] = i.notional

        if any(v is None for v in self.__symbol_info.values()):
            raise BotError("some values are None in symbol_info", BotAction.EXIT)
        
    # propertys
    @property
    def available_quote_asset_balance(self)->Decimal:
        res = self.api_manager.get_account_balance().get_asset(self.quote_asset)
        return res.available_balance

    @property
    def total_quote_asset_balance(self)->Decimal:
        res = self.api_manager.get_account_balance().get_asset(self.quote_asset)
        return res.balance
    
    @property
    def leverage(self)->Decimal:
        if self.__leverage is None:
            self.update_symbol_config()
        return self.__leverage
    
    # getter use setter to set leverage
    @leverage.setter
    def leverage(self, val:float)->None:
        # prevent set same value error
        if self.leverage != val:
            self.api_manager.change_leverage(self.settings.engine_settings.symbol, val)
            self._log_handle.write_log(f"new leverage={val}", LogLevel.INFO)
            self.__leverage = val

    @property
    def margin_type(self)->MarginType:
        if self.__margin_type is None:
            self.update_symbol_config()
        return self.__margin_type

    @margin_type.setter
    def margin_type(self, val:MarginType)->None:
        if self.margin_type != val:
            self.api_manager.change_margin_type(self.settings.engine_settings.symbol, val)
            self.__margin_type = val

    @property
    def dual_side_position(self)->bool:
        if self.__dual_side_position is None:
            self.update_accout_config()

        return self.__dual_side_position
    
    @dual_side_position.setter
    def dual_side_position(self, val:bool)->None:
        if self.dual_side_position != val:
            self.api_manager.change_position_mode(val)
            self.__dual_side_position = val

    @property
    def multi_assets_margin(self)->bool:
        if self.__multi_assets_margin is None:
            self.update_accout_config()

        return self.__multi_assets_margin
    
    @multi_assets_margin.setter
    def multi_assets_margin(self, val:bool)->bool:
        if self.multi_assets_margin != val:
            self.api_manager.change_multi_assets_mode(val)
            self.__multi_assets_margin = val

        return self.__multi_assets_margin
    
    @property
    def base_asset(self)->str:
        if self.__base is None:
            self.update_exchange_info()
        return self.__base
        
    @property
    def quote_asset(self)->str:
        if self.__quote is None:
            self.update_exchange_info()
        return self.__quote
    
    @property
    ### chage dict to basemodel
    def symbol_info(self)->dict:
        if self.__symbol_info is None:
            self.update_exchange_info()
        return self.__symbol_info

    @log_lifecycle
    def quote_asset2order_size(self, qty:Decimal, order_type:OrderType=OrderType.LIMIT)->Decimal:
        if qty > self.available_quote_asset_balance*self.margin_buffer:
            raise BotError(f"available balance can't support order: {qty} > {self.available_quote_asset_balance}*{self.margin_buffer}", BotAction.EXIT)
        
        prefix = order_type.get_type()
        max_qty = self.symbol_info[f"{prefix}_max_qty"]
        min_qty = self.symbol_info[f"{prefix}_min_qty"]
        step_size = self.symbol_info[f"{prefix}_step_size"]

        # get current price
        price = self.api_manager.get_price_ticker(self.settings.engine_settings.symbol).price
        
        # rounding
        base_qty = self.floor_step(qty*self.leverage/price, step_size)
        
        # filter
        if base_qty*price<self.symbol_info["min_notional"]:
            raise BotError("order notional lower than required", BotAction.EXIT)

        if min_qty > base_qty:
            raise BotError("base qty lower than min qty", BotAction.EXIT)
        
        if max_qty < base_qty:
            raise BotError("base qty greater than max qty", BotAction.EXIT)
        
        return base_qty

class BackTestEngine(BaseEngine):
    '''handle mode: BACKTEST, BACKTEST_SINGLE'''
    def __init__(self, settings):
        super().__init__(settings)
        self.trade_data = []

        # load dfs 
        paths = self.settings.signal_settings.df_config.get_all_path()
        dfs = {k:self.read_kline_csv(v) for k,v in paths.items()} # maybe use return conkline ???

        self.meta_df = self.signal_handle.config_signal(dfs)
        self.meta_dict = self.meta_df.reset_index().to_dict("records")

        # init df helper
        self._cur_idx = 0 # so next is 0
        self._max_idx = len(self.meta_df) - 1
        self.action_chain = []
        self.pre_stat = None

        self.entry = [self.meta_df.index[0]]

        #TODO: also need to read real trade data for entry points
        # for debuging purpose
        if self.settings.engine_settings.mode == BotMode.BACKTEST_SINGLE:
            pass
    
    def step(self):
        res = super().step()
        if not res:
            with open("trades.jsonl", "w") as f:
                f.writelines(self.trade_data)

        return res
    
    @staticmethod
    def read_kline_csv(path):
        csv_converters = {
            "open_price":Decimal,
            "high_price":Decimal,
            "low_price":Decimal,
            "close_price":Decimal,
            "volume":Decimal,
            "quote_asset_volume":Decimal,
            "taker_buy_volume":Decimal,
            "taker_buy_quote_asset_volume":Decimal
        }
        # include type casting
        res = pd.read_csv(path, converters=csv_converters)

        # field check
        fields = {
            "open_time", 
            "open_price", 
            "high_price", 
            "low_price", 
            "close_price", 
            "volume", 
            "close_time", 
            "quote_asset_volume", 
            "trade_num", 
            "taker_buy_volume", 
            "taker_buy_quote_asset_volume", 
            "ignore"
        }
        if set(res.columns) != fields:
            raise BotError(f"field miss match: {set(res.columns)}", BotAction.EXIT)
        
        return res
    
    def get_row(self)->pd.Series|None:
        '''get current row'''
        if self._cur_idx > self._max_idx:
            return None
        row = self.meta_dict[self._cur_idx]
        return row

    def set_row_price(self, open_price:Decimal=None, close_price:Decimal=None, high_price:Decimal=None, low_price:Decimal=None):
        data = locals()
        data = {x for x in data if x is not None and x is not self}
        ### need to add self.row
        # row = self.get_row()
        # if row and self._cur_idx <= self._max_idx :
        #     row = row.map(data)
        #     self.meta_df.iloc[self._cur_idx] = row

    def action(self, stat)->None:
        # to n next
        if stat.wait > 0: # set to next n row, execute in next round
            self._cur_idx += stat.wait 
            self.action_chain = []
            if stat.event:
                self.trade_data.append(stat.event.to_jsons()+"\n")

        # to next
        elif len(self.action_chain) > 10: # error exit, action chain looped
            self._log_handle.write_log(f"action stack overflow: {self.action_chain}", LogLevel.INFO)
            # rewind one step
            self.strat_handle.stat = self.action_chain[-1]
            self._cur_idx += 1
            self.action_chain = []

        # to next
        elif stat in self.action_chain:
            self._log_handle.write_log(f"{stat, self.action_chain}", LogLevel.DEBUG)
            # rewind avoid using repeated status
            self.strat_handle.stat = self.action_chain[-1]
            self._cur_idx += 1
            self.action_chain = []

        # stay cur (non repeated status)
        else:
            ### need to reset open price to order price
            self.action_chain.append(stat)
            if stat.event:
                self.trade_data.append(stat.event.to_jsons()+"\n")

    def get_new_balance(self):
        pass

class Engine(Base):
    def __init__(self, settings:TradingBotKwargs):
        super().__init__()
        self.engine = None
        mode = settings.engine_settings.mode
        if mode in (BotMode.LIVE_TRADE, BotMode.TEST_TRADE):
            self.engine = LiveEngine(settings)

        elif mode in (BotMode.BACKTEST, BotMode.BACKTEST_SINGLE):
            self.engine = BackTestEngine(settings)

        elif mode == BotMode.RECORD:
            self.engine = RecordEngine(settings)

    # integrate all engine
    def _loop(self):
        res = self.engine.step()
        if not res:
            # engine finish
            self.exit = True
            return
