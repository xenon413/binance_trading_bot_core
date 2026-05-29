from __future__ import annotations
from typing import Optional, Union
from decimal import Decimal
from pydantic import model_validator
import os

from ..my_base_model import MyBaseModel
from ..constants import BotMode, Symbol, CandleInterval, MarginType, BotAction
from ..interface.interface import StratType, StratInterface
from ..exceptions import BotError

### ensuer that all Decimal var is entered with str

# ---- signal settings ----
class SMAIndexConfig(MyBaseModel):
    window:int # rollingn window of sma index
    base_price:str # usually use close_price

class SMACrossConfig(MyBaseModel):
    sma1:str # the faster index name
    sma2:str # the slower index name

class SMATrendConfig(MyBaseModel):
    sma:str # the target sma name
    length:int # the length that count as a trend

class SMAAdjustConfig(MyBaseModel):
    sma:str
    new_price:str
    mask:str

class RelPosConfig(MyBaseModel):
    s1:str
    s2:str

class ExtremeConfig(MyBaseModel):
    col:str
    window:int

class ExcludeCountConfig(MyBaseModel):
    col:str
    window:int
    exclude:int

class IndexConfig(MyBaseModel): # add any when needed
    sma_index:Optional[dict[str, SMAIndexConfig]] = None
    sma_cross:Optional[dict[str, SMACrossConfig]] = None
    sma_trend:Optional[dict[str, SMATrendConfig]] = None
    sma_adjust:Optional[dict[str, SMAAdjustConfig]] = None
    rel_pos:Optional[dict[str, RelPosConfig]] = None
    extreme:Optional[dict[str, ExtremeConfig]] = None
    exclude_count:Optional[dict[str, ExcludeCountConfig]] = None

    def _check_config_one(self):
        if not any(getattr(self, field) for field in self.__class__.model_fields):
            raise BotError("IndexConfig need at least one config", BotAction.EXIT)

class DFEntry(MyBaseModel):
    symbol:Symbol # live/backtest/record
    interval:CandleInterval # live/backtest/record
    index:IndexConfig # live/backtest/record
    path:Optional[str] = None # backtest

class DFConfig(MyBaseModel):
    main:DFEntry
    merge:Optional[dict[str, IndexConfig]]=None
    others:Optional[dict[str, DFEntry]]=None

    def get_all_path(self)->dict[str, str]|None:
        # not in the correct mode
        if self.main.path == None:
            return
        path = {"main":self.main.path}
        if self.others:
            path |= {k:v.path for k, v in self.others.items()}
        return path

    def get_all_df_name(self)->list[str]:
        lst = ["main"]
        if self.merge:
            lst.append("merge")

        if self.others:
            lst.extend(self.others.keys())

        return lst

    def get_all_entry(self)->list[dict[str, DFEntry]]:
        entry = {"main":self.main}
        if self.merge:
            entry["merge"] = self.merge

        if self.others:
            for k, v in self.others.items():
                entry[k] = v
        return entry
    
    def get_config(
            self, df_name:str, index_type:str, index_name:str
        )->SMAIndexConfig|SMACrossConfig|SMATrendConfig|SMAAdjustConfig|\
            RelPosConfig|ExtremeConfig|ExcludeCountConfig:
    
        if df_name == "main":
            return getattr(self.main.index, index_type)[index_name]
        
        elif df_name == "merge":
            return getattr(self.merge["index"], index_type)[index_name]
        
        else:
            return getattr(self.others[df_name].index, index_type)[index_name]

    def get_df_interval(self, df_name:str)->CandleInterval:
        if df_name == "main":
            return self.main.interval
        
        elif df_name == "merge":
            return self.main.interval
        
        else:
            return self.others[df_name].interval
        
class SignalSettings(MyBaseModel):
    df_config:DFConfig
    df_config_order:list[tuple[str, str, str]]

    def match_order(self):
        ### complete later ensure df_config and df_config_order matchs
        pass
    
# ---- strat settings ----
class LeverageConfig(MyBaseModel):
    base:int
    others:Optional[dict[str, int]] = None

class StratConfig(MyBaseModel):
    leverage:LeverageConfig
    others:Optional[dict[str, Decimal|int]] = None

class StratKwargs(MyBaseModel):
    strat_config:StratConfig

class StratSettings(MyBaseModel):
    target:StratType
    kwargs:StratKwargs

    def create_instance(self)->StratInterface:
        return self.target(self.kwargs)

# ---- engine settings ----
class EngineSettings(MyBaseModel):
    mode:BotMode # live/backtest/record
    symbol:Symbol # live/backtest/record
    dual_side_position:Optional[bool] = None # live
    multi_assets_margin:Optional[bool] = None # live
    margin_type:Optional[MarginType] = None # live
    drag_order_threash:Optional[Decimal] = None # live
    max_reorder:Optional[int] = None # live
    margin_buffer:Decimal # live/backtest/record
    margin_limit:tuple[int, int] # live/backtest/record
    init_margin_asset_balance:Optional[Decimal] = None # backtest/record

    def _check_req(self):
        def clean_up(req:set[str], *args):
            others = set(item for sub in args for item in sub)-req
            failed_req = [f for f in req if getattr(self, f) is None]
            if failed_req:
                raise BotError(f"in {self.__class__.__name__} under {self.mode} missing req: {failed_req}", BotAction.EXIT)
            
            for i in others:
                setattr(self, i, None)

        live_req = {
            "dual_side_position",
            "multi_assets_margin",
            "margin_type",
            "drag_order_threash",
            "max_reorder"
        }

        backtest_req = {"init_margin_asset_balance",}

        record_req = {"init_margin_asset_balance",}

        all_req = [live_req, backtest_req, record_req]

        rot_map = {
            BotMode.LIVE_TRADE:0,
            BotMode.TEST_TRADE:0,
            BotMode.BACKTEST:1,
            BotMode.RECORD:2
        }
        rot = rot_map[self.mode]
        all_req = all_req[rot:] + all_req[:rot]
        clean_up(*all_req)
        
# ---- integrate ----
class TradingBotKwargs(MyBaseModel):
    engine_settings:EngineSettings
    signal_settings:SignalSettings
    strat_settings:StratSettings

    def _check_df_path(self):
        mode = self.engine_settings.mode
        if mode in (BotMode.LIVE_TRADE, BotMode.TEST_TRADE, BotMode.RECORD):
            # clean main
            self.signal_settings.df_config.main.path = None

            # clean others
            if self.signal_settings.df_config.others:
                for val in self.signal_settings.df_config.others.values():
                    val.path = None

        if mode == BotMode.BACKTEST:
            all_path = [self.signal_settings.df_config.main.path]
            
            if self.signal_settings.df_config.others:
                for val in self.signal_settings.df_config.others.values():
                    all_path.append(val.path)

            for p in all_path:
                if p is None:
                    raise BotError(f"path missing in df_config", BotAction.EXIT)
                
                if not os.path.exists(p):
                    raise BotError(f"in df_config path do not exist: {p}", BotAction.EXIT)

