from __future__ import annotations
from pydantic import Field, ConfigDict, model_validator
from decimal import Decimal
import pandas as pd
from queue import Queue
import queue
from collections import deque
from typing import Optional, Callable, Generic, TypeVar, Type, Literal, Any
from enum import Enum
from abc import ABC, abstractmethod
import time

from ...constants import (
    Symbol, ContractType, CandleInterval
)
from ...decorators import redirect
from ..api_return_schema import MyBaseModel

# template
class Params(MyBaseModel, ABC):
    @property
    @abstractmethod
    def endpoint(self)->str:...

class Return(MyBaseModel, ABC):
    def _validator(self, timestamp:int, window:int=5000)->bool:
        cur_time = int(time.time()*1000)
        return abs(cur_time - timestamp) < window

    @property
    @abstractmethod
    def valid(self)->bool:...

P = TypeVar("P", bound=Params) # Parameter Type
R = TypeVar("R", bound=Return) # Return Type

# define kline status in WSKlineDF class 
class KlineStatus(MyBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    is_close:bool
    cur_open:int
    next_open:int
    df:pd.DataFrame
    buff:StreamBuffer[ContKlineParams, ContKlineReturn]
    event_time:int

class KlineStreamStatus(MyBaseModel):
    '''[endpoint, status]'''
    kline_status:dict[str, KlineStatus] = Field(default_factory=dict)

    def set_kline_status(self, is_close:bool, cur_open:int, df:pd.DataFrame, buff:StreamBuffer[ContKlineParams, ContKlineReturn], params:ContKlineParams):
        status = KlineStatus(
            is_close=is_close,
            cur_open=cur_open,
            next_open=cur_open + params.interval.ms,
            df=df,
            buff=buff,
            event_time=int(time.time()*1000)
        )

        self.kline_status[params.endpoint] = status

    def values(self)->list[KlineStatus]:
        return list(self.kline_status.values())
    
    def items(self):
        return self.kline_status.items()
    
    def get(self, key:str)->KlineStatus|None:
        return self.kline_status.get(key)
    
class _SingleBuffer:
    def __init__(self):
        self.value = None
    
    def put(self, val:Any)->None:
        self.value = val

    @redirect("put")
    def put_nowait(self, val:Any)->None:...
        
    def get(self)->Any:
        return self.value

    @redirect("get")
    def get_nowait(self)->None:...

    def qsize(self)->int:
        return 1 if self.value is not None else 0
    
# define routing table in manager
class StreamBuffer(Generic[P, R]):
    def __init__(self, mode:Literal["queue", "sampling"], endpoint:EndPoint[P, R]):
        self.max_size = 100 if mode == "queue" else 1
        self.endpoint = endpoint
        self.mode = mode
        self.buffer = Queue(self.max_size) if mode == "queue" else _SingleBuffer()

    def push(self, data:R|dict)->None:
        # validator
        if isinstance(data, dict):
            data = self.endpoint.return_type.model_validate(data)
        
        elif not isinstance(data, self.endpoint.return_type):
            # TODO: add logger
            return
        
        try:
            self.buffer.put_nowait(data)
        except queue.Full:
            # TODO: add logger
            return

    def pop(self)->R|None:
        try:
            return self.buffer.get_nowait()
        except queue.Empty:
            return None

    def size(self)->int:
        return self.buffer.qsize()
    
    def is_max_size(self)->bool:
        return self.size() == self.max_size
    
class RoutingTable(MyBaseModel):
    '''[endpoint, mode, buff]'''
    model_config = ConfigDict(arbitrary_types_allowed=True)
    routes: dict[str, dict[str, list[StreamBuffer[P, R]]]] = Field(default_factory=dict)

    def buff_exist(self, endpoint:str, mode:Literal["queue", "sampling"])->bool:
        return ((r:=self.routes.get(endpoint)) is not None) and (r.get(mode) is not None)
    
    def endpoint_exist(self, endpoint:str)->bool:
        return self.routes.get(endpoint) is not None

    def add_route(self, buff:StreamBuffer[P, R], params:P):
        # init route
        route = self.routes.get(params.endpoint)
        if route is None:
            self.routes[params.endpoint] = {}

        # init buff
        if self.routes.get(params.endpoint).get(buff.mode) is None:
            self.routes[params.endpoint][buff.mode] = [buff]
            
        else:
            self.routes[params.endpoint][buff.mode].append(buff)

    def dispatch(self, endpoint:str, data:dict|R)->None:
        if (route:=self.routes.get(endpoint)) is None: return
        for r in route.values():
            for buff in r:
                buff.push(data)
        
    def keys(self)->list:
        '''returns all endpoints'''
        return list(self.routes.keys())
        
# ---- params ----
class SymbolPriceTickerParams(Params):
    '''using cont-kline params to implement'''
    pair:Symbol
    contractType:Optional[ContractType] = ContractType.PERPETUAL
    interval:Optional[CandleInterval] = CandleInterval.MIN_1

    @property
    def endpoint(self)->str:
        return f"{self.pair.lower()}_{self.contractType.lower()}@continuousKline_{self.interval}"
    
class ContKlineParams(Params):
    pair:Symbol
    contractType:ContractType
    interval:CandleInterval

    @property
    def endpoint(self)->str:
        return f"{self.pair.lower()}_{self.contractType.lower()}@continuousKline_{self.interval}"
    
class OrderBookTickerParams(Params):
    symbol:Symbol

    @property
    def endpoint(self)->str:
        return f"{self.symbol.lower()}@bookTicker"
    
# ---- return values ----
class SymbolPriceTickerReturn(Return):
    '''not a real endpoint'''
    symbol:Symbol
    price:Decimal
    trans_time:int

    # create a process to handle contkline incoming data
    @model_validator(mode="before")
    @classmethod
    def converter(cls, data:dict)->dict:
        # validate init data
        valid = ContKlineReturn(data)
        
        # convert
        res = {"symbol":valid.symbol, "price":valid.kline.close_price, "trans_time":valid.event_time}
        return res
    
    @property
    def valid(self):
        return super()._validator(self.trans_time)
        
class _Kline(MyBaseModel):
    # keep same order as rest api
    open_time:int=Field(alias="t")
    open_price:Decimal=Field(alias="o")
    high_price:Decimal=Field(alias="h")
    low_price:Decimal=Field(alias="l")
    close_price:Decimal=Field(alias="c")
    volume:Decimal=Field(alias="v")
    close_time:int=Field(alias="T")
    quote_asset_volume:Decimal=Field(alias="q")
    trade_num:int=Field(alias="n")
    taker_buy_volume:Decimal=Field(alias="V")
    taker_buy_quote_asset_volume:Decimal=Field(alias="Q")
    ignore:str=Field(alias="B")
    # addition not in the rest api df
    interval:CandleInterval=Field(alias="i")
    first_update_id:int=Field(alias="f")
    last_update_id:int=Field(alias="L")
    is_close:bool=Field(alias="x")

    @property
    def df(self)->pd.DataFrame:
        '''return a raw one row df'''
        return pd.DataFrame([self.model_dump()])

    @property
    def df_clean(self) -> pd.DataFrame:
        '''return a one row df, cleaned to match rest api df'''
        return pd.DataFrame([self.model_dump(exclude={"interval", "first_update_id", "last_update_id", "is_close"})])

class ContKlineReturn(Return):
    event_type:str=Field(alias="e")
    event_time:int=Field(alias="E")
    symbol:Symbol=Field(alias="ps")
    contract_type:ContractType=Field(alias="ct")
    kline:_Kline=Field(alias="k")

    def to_symbol_price_ticker(self):
        return SymbolPriceTickerReturn(self)


    @property
    def valid(self):
        return super()._validator(self.event_time)
       
class OrderBookTickerReturn(Return):
    event_type:str=Field(alias="e")
    event_time:int=Field(alias="E")
    update_id:int=Field(alias="u")
    trans_time:int=Field(alias="T")
    symbol:Symbol=Field(alias="s")
    bid_price:Decimal=Field(alias="b")
    bid_qty:Decimal=Field(alias="B")
    ask_price:Decimal=Field(alias="a")
    ask_qty:Decimal=Field(alias="A")

    @property
    def valid(self):
        return super()._validator(self.trans_time)
    
class EndPoint(MyBaseModel, Generic[P, R]):
    param_type:Type[P]
    return_type:Type[R]
    # TODO: switch to str enum 
    path:Literal["public", "market", "private"]

class StreamEndpointCollection(Enum):
    ORDER_BOOK_TICKER = EndPoint(
        param_type=OrderBookTickerParams,
        return_type=OrderBookTickerReturn,
        path="public"
    )

    CONT_KLINE = EndPoint(
        param_type=ContKlineParams,
        return_type=ContKlineReturn,
        path="market"
    )

    SYMBOL_PRICE_TICKER = EndPoint(
        param_type=SymbolPriceTickerParams,
        return_type=SymbolPriceTickerReturn,
        path="market"
    )