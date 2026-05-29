from decimal import Decimal
import pandas as pd
from .rest_api import RestEndpointCollection, BinanceRestapi
from .ws_api import WSEndpointCollection, WSapi
from .ws_stream import WSKlineDF, WSManager, WSFetch, StreamEndpointCollection
import time
from ..decorators import log_lifecycle

# returns
from .rest_api.rest_api_schema import (
    RawReturn, ContKlineReturn, ServerTimeReturn,
    ExchangeInfoReturn, SymbolConfigReturn,
    AccountConfigReturn, ChangeLeverageReturn, AutoCancelOrderReturn, PositionInfoReturn
)

from .api_return_schema import (
    SymbolPriceTickerReturn, OrderBookTickerReturn, NewOrderReturn, ModifyOrderReturn,
    CancelOrderReturn, QueryOrderReturn, AccountBalanceReturn
)

from typing import Optional
from ..my_base_model import MyBaseModel
from ..log_handle import LogHandle
from ..schema.bot_schema import SignalSettings, DFEntry
from ..constants import (
    LogLevel, Symbol, CandleInterval, ContractType, OrderSide, 
    PositionSide, OrderType, TimeInForce, PriceMatch, MarginType,
    OrderStatus
)
from ..exceptions import BotAction, BotError
from ..schema.schema import ExecuteOrder

class DragOrderReturn(MyBaseModel):
    open_time:Optional[int]
    open_price:Optional[Decimal]
    filled_canceled_time:Optional[int]
    filled_price:Optional[Decimal] # will be 0 if canceled
    filled_qty:Optional[Decimal] # will be 0 if canceled

#TODO: add to config later
ENABLE_WS = False # disable till error handle complete
ENABLE_WS_STREAM = False # disable till fixed

#TODO: make sure all the returns that gets from different method have the same shape
class APIManager:
    def __init__(self, test:bool, signal_setting:SignalSettings)->None:
        self.settings = signal_setting
        self.enable_ws = ENABLE_WS
        self.enable_ws_stream = ENABLE_WS_STREAM
        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)

        self.rest_api_handle = BinanceRestapi(test)

        if self.enable_ws:
            self.ws_api_handle = WSapi(test)
        
        if self.enable_ws_stream:
            self.manager = WSManager(test)
            self.ws_kline_handle = WSKlineDF(self.manager, self.rest_api_handle)
            self.ws_fetcher = WSFetch(self.manager)

        # start ws stream service
        # signal_setting.df_config.get_all_entry()
        # manager = WSManager()
        # self.ws_kline_handle = WSKlineDF(manager, self.rest_api_handle, )

    def get_cont_kline_df(self, symbol:Symbol, interval:CandleInterval)->pd.DataFrame:
        '''get current 1500 continuous kline'''

        # get with ws stream
        if self.enable_ws_stream:
            res = self.ws_kline_handle.get_df(symbol, interval)
            if res is not None:
                # res.to_csv("ws_stream.csv")
                return res
            
        # get with rest api
        # fuck ass who use pair instead of symbol only this endpoint 
        param = {"pair":symbol, "interval":interval, "contractType":ContractType.PERPETUAL, "limit":1500}
        res = self.rest_api_handle.request(RestEndpointCollection.CONT_KLINE.value, param)
        # res.df.to_csv("rest_api.csv")
        return res.df

    def get_best_book_price(self, symbol:Symbol)->OrderBookTickerReturn:
        param = {"symbol":symbol}

        # get with ws stream
        if self.enable_ws_stream:
            p = StreamEndpointCollection.ORDER_BOOK_TICKER.value.param_type.model_validate(param)
            res = self.ws_fetcher.get_data(StreamEndpointCollection.ORDER_BOOK_TICKER.value, p)
            if res is not None:
                return res
            
        # get with ws
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.ORDER_BOOK_TICKER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.ORDER_BOOK_TICKER.value, param)
        return res

    def get_price_ticker(self, symbol:Symbol)->SymbolPriceTickerReturn:
        param = {"symbol":symbol}

        # get with ws stream
        if self.enable_ws_stream:
            p = StreamEndpointCollection.SYMBOL_PRICE_TICKER.value.param_type.model_validate(param)
            res = self.ws_fetcher.get_data(StreamEndpointCollection.SYMBOL_PRICE_TICKER.value, p)
            if res is not None:
                return res            
        # get with ws
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.SYMBOL_PRICE_TICKER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.SYMBOL_PRICE_TICKER.value, param)
        return res
    
    def get_server_time(self)->ServerTimeReturn:
        res = self.rest_api_handle.request(RestEndpointCollection.SERVER_TIME.value)
        return res
    
    def get_exchange_info(self)->ExchangeInfoReturn:
        res = self.rest_api_handle.request(RestEndpointCollection.EXCHANGE_INFO.value)
        return res
    
    def get_account_balance(self)->AccountBalanceReturn:
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.ACCOUNT_BALANCE.value)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.ACCOUNT_BALANCE.value)
        return res

    def get_account_config(self)->AccountConfigReturn:
        res = self.rest_api_handle.request(RestEndpointCollection.ACCOUNT_CONFIG.value)
        return res
    
    def get_symbol_config(self, symbol:Symbol=None)->SymbolConfigReturn:
        '''with symbol passed return list with len=1'''
        param = {"symbol":symbol}
        res = self.rest_api_handle.request(RestEndpointCollection.SYMBOL_CONFIG.value, param)
        return res

    def get_position_info(self, symbol:Symbol=None)->PositionInfoReturn:
        param = {"symbol":symbol}
        res = self.rest_api_handle.request(RestEndpointCollection.POSITION_INFO.value, param)
        return res

    def new_order(
        self, symbol:Symbol, side:OrderSide, type:OrderType, positionSide:PositionSide=None,
        timeInForce:TimeInForce=None, quantity:Decimal=None, reduceOnly:str=None,
        price:Decimal=None, newClientOrderId:str=None, newOrderRespType:str=None,
        priceMatch:PriceMatch=None, selfTradePreventionMode:str=None, goodTillDate:str=None
    )->NewOrderReturn:
        param = {
            "symbol":symbol, 
            "side":side, 
            "type":type, 
            "positionSide":positionSide, 
            "timeInForce":timeInForce,
            "quantity":quantity,
            "reduceOnly":reduceOnly,
            "price":price,
            "newClientOrderId":newClientOrderId,
            "newOrderRespType":newOrderRespType,
            "priceMatch":priceMatch,
            "selfTradePreventionMode":selfTradePreventionMode,
            "goodTillDate":goodTillDate
        }
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.NEW_ORDER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.NEW_ORDER.value, param)
        return res
    
    def query_order(self, symbol:Symbol, orderId:int=None, origClientOrderId:str=None)->QueryOrderReturn:
        param = {"symbol":symbol, "orderId":orderId, "origClientOrderId":origClientOrderId}
        
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.QUERY_ORDER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.QUERY_ORDER.value, param)
        return res
    
    def modify_order(self, symbol:Symbol, quantity:Decimal, side:OrderSide, orderId:int=None, origClientOrderId:str=None, price:Decimal=None, priceMatch:PriceMatch=None)->ModifyOrderReturn|BotError:
        param = {
            "symbol":symbol, 
            "quantity":quantity, 
            "side":side, 
            "orderId":orderId, 
            "origClientOrderId":origClientOrderId, 
            "price":price, 
            "priceMatch":priceMatch
        }
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.MODIFY_ORDER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.MODIFY_ORDER.value, param)
        return res
    
    def cancel_order(self, symbol:Symbol, orderId:int=None, origClientOrderId:str=None)->CancelOrderReturn:
        param = {"symbol":symbol, "orderId":orderId, "origClientOrderId":origClientOrderId}
        
        if self.enable_ws:
            res = self.ws_api_handle.send(WSEndpointCollection.CANCEL_ORDER.value, param)
            if res is not None:
                return res.result
        
        res = self.rest_api_handle.request(RestEndpointCollection.CANCEL_ORDER.value, param)
        return res
    
    def cancel_all_order(self, symbol:Symbol)->RawReturn:
        param = {"symbol":symbol}
        res = self.rest_api_handle.request(RestEndpointCollection.CANCEL_ALL_ORDER.value, param)
        return res

    def auto_cancel_order(self, symbol:Symbol, countdownTime:int)->AutoCancelOrderReturn:
        '''countdownTime as ms'''
        param = {"symbol":symbol, "countdownTime":countdownTime}
        res = self.rest_api_handle.request(RestEndpointCollection.AUTO_CANCEL_ORDER.value, param)
        return res

    # need no exist order to change
    def change_margin_type(self, symbol:Symbol, margintype:MarginType)->RawReturn:
        param = {"symbol":symbol, "margintype":margintype}
        res = self.rest_api_handle.request(RestEndpointCollection.CHANGE_MARGIN_TYPE.value, param)
        return res
    
    # need no exist order to change
    def change_position_mode(self, dual_side_position:bool)->RawReturn:
        param = {"dualSidePosition":dual_side_position}
        res = self.rest_api_handle.request(RestEndpointCollection.CHANGE_POSITION_MODE.value, param)
        return res

    def change_leverage(self, symbol:Symbol, leverage:int)->ChangeLeverageReturn:
        param = {"leverage":leverage, "symbol":symbol}
        res = self.rest_api_handle.request(RestEndpointCollection.CHANGE_LEVERAGE.value, param)
        return res

    # need all margin type be cross to change to multi assets mode 
    def change_multi_assets_mode(self, multi_assets_margin:bool)->RawReturn:
        param = {"multiAssetsMargin":multi_assets_margin}
        res = self.rest_api_handle.request(RestEndpointCollection.CHANGE_MULTI_ASSETS_MODE.value, param)
        return res
    
    # combination utils
    ### not finished yet
    def close_all_position_order(self, symbol:Symbol):
        '''close all position and order'''
        param = {"symbol":symbol}
        
        # cancel all order
        self.cancel_all_order(param)

        # sell all position
        ### add rest api endpoint for position info
        ### https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Position-Information-V3

        self.new_order()

    @log_lifecycle
    def drag_order(self, symbol:Symbol, side:OrderSide, positionSide:PositionSide, quantity:Decimal, auto_cancel:int=0, pct_diff_thresh:Decimal=0.0001)->ExecuteOrder:
        ''' auto cancel unit as milliseconds'''
        info = {}
        # set auto cancel
        if auto_cancel:
            self.auto_cancel_order(symbol, auto_cancel)
        
        # def order
        order = lambda qty:self.new_order(
            symbol=symbol,
            side=side,
            positionSide=positionSide,
            type="LIMIT",
            timeInForce="GTX",
            quantity=qty,
            priceMatch="QUEUE"
        )
        
        # initialize order
        order_res = order(quantity)
        info["time"] = order_res.update_time
        info["open_price"] = order_res.price
        info["open_qty"] = order_res.orig_qty

        exit = False
        while True:
            query_res = self.query_order(symbol, order_res.order_id)
            self._log_handle.write_log(f"order id: {order_res.order_id} order status: {query_res.status}", LogLevel.DEBUG)

            # check order status
            if query_res.status == OrderStatus.FILLED:
                exit = True

            elif query_res.status == OrderStatus.REJECTED:
                raise BotError(f"order rejected, query res: {query_res}", BotAction.EXIT)

            elif query_res.status == OrderStatus.CANCELED:
                exit = True

            elif query_res.status == OrderStatus.EXPIRED:
                raise BotError(f"order expired, query res: {query_res}", BotAction.EXIT)
            
            # record but no action
            elif query_res.status == OrderStatus.PARTIALLY_FILLED:
                self._log_handle.write_log(f"order partially filled, query res: {query_res}", LogLevel.DEBUG)

            # get order book
            book = self.get_best_book_price(symbol)
            book_price = book.bid_price if side == OrderSide.BUY else book.ask_price

            # actions
            if exit:
                info["filled_canceled_time"] = query_res.update_time
                info["filled_price"] = query_res.avg_price
                info["filled_qty"] = query_res.executed_qty
                break

            if abs(book_price-order_res.price)/book_price > pct_diff_thresh:
                self._log_handle.write_log(f"before modify order, executed qty: {query_res.executed_qty}", LogLevel.DEBUG)

                res = None
                try:
                    res = self.modify_order(
                        orderId=order_res.order_id,
                        symbol=Symbol.BTCUSDC,
                        side=side,
                        priceMatch=PriceMatch.QUEUE,
                        quantity=query_res.orig_qty-query_res.executed_qty
                    )
                except Exception as e:
                    self._log_handle.write_log(f"failed to modify order: {e}", LogLevel.WARNING)

                if isinstance(res, ModifyOrderReturn):
                    order_res = res

            time.sleep(1)

        # reset auto cancel
        if auto_cancel:
            self.auto_cancel_order(symbol, 0)

        return ExecuteOrder.model_validate(info)
    
    ### maybe write it here?
    ### if write here there's issue about accessing base/quote asset
    # def quote2base_asset(self, qty:Decimal)->Decimal:
    #     '''quote asset qty to base asset qty'''

