from __future__ import annotations
from pydantic import RootModel, Field
from typing import TypedDict, Generic, TypeVar, Type, Optional, List
from enum import Enum
from decimal import Decimal

from ...constants import (
    Symbol, OrderType, TimeInForce, OrderSide, PositionSide, PriceMatch, Bool
)

from ..api_return_schema import (
    SymbolPriceTickerReturn, OrderBookTickerReturn, NewOrderReturn, ModifyOrderReturn,
    MyBaseModel, CancelOrderReturn, QueryOrderReturn, AccountBalanceReturn
)




P = TypeVar("P") # Parameter Type
R = TypeVar("R", bound=MyBaseModel|RootModel) # Return Type

# ---- params ----
class NoParams(TypedDict):...

class SymbolPriceTickerParams(TypedDict):
    symbol:Symbol

class OrderBookTickerParams(TypedDict):
    symbol:Symbol

class NewOrderParams(TypedDict):
    symbol:Symbol
    side:OrderSide
    positionSide:Optional[PositionSide]=None
    type:OrderType
    timeInForce:Optional[TimeInForce]=None
    quantity:Optional[Decimal]
    reduceOnly:Optional[Bool]
    price:Optional[Decimal]
    newClientOrderId:Optional[str]
    stopPrice:Optional[Decimal]
    closePosition:Optional[Bool]
    activationPrice:Optional[Decimal]
    callbackRate:Optional[Decimal]
    workingType:Optional[str]
    priceProtect:Optional[Bool] # Note that need to use cap strings when in use mf ass tf only in ws api order not in rest api order
    newOrderRespType:Optional[str]
    priceMatch:Optional[PriceMatch]
    selfTradePreventionMode:Optional[str]
    goodTillDate:Optional[int]

class ModifyOrderParams(TypedDict):
    orderId:Optional[int]
    origClientOrderId:Optional[str]
    symbol:Symbol
    side:OrderSide
    quantity:Decimal
    price:Decimal
    priceMatch:PriceMatch

class CancelOrderParams(TypedDict):
    symbol:Symbol
    orderId:Optional[int]=None
    origClientOrderId:Optional[str]=None

class QueryOrderParams(TypedDict):
    symbol:Symbol
    orderId:Optional[int]=None
    origClientOrderId:Optional[str]=None

# ---- return schema ----
class _LimitItem(MyBaseModel):
    rate_limit_type:str=Field(alias="rateLimitType")
    interval:str
    interval_num:int=Field(alias="intervalNum")
    limit:int
    count:int

class RateLimit(RootModel):
    '''
    three types of limit:
    ORDERS in SECOND
    ORDERS in MINUTE
    REQUEST_WEIGHT in MINUTE
    '''
    root: List[_LimitItem]

    def __iter__(self):
        return iter(self.root)
    
    def __getitem__(self, item):
        return self.root[item]
    
    def check_limit(pct_threash:float=0.8)->None:
        pass

class ReturnSchema(MyBaseModel, Generic[R]):
    id:str
    status:int
    result:R
    rateLimits:RateLimit

# ---- endpoints ----
class EndPoint(MyBaseModel, Generic[P, R]):
    method:str # name
    param_type:Type[P]
    return_res_type:Type[R]
    signed:bool
    
    @property
    def return_type(self):
        return ReturnSchema[self.return_res_type]

class WSEndpointCollection(Enum):
    SYMBOL_PRICE_TICKER = EndPoint(
        method="ticker.price",
        param_type=SymbolPriceTickerParams,
        return_res_type=SymbolPriceTickerReturn,
        signed=False
    )

    ORDER_BOOK_TICKER = EndPoint(
        method="ticker.book",
        param_type=OrderBookTickerParams,
        return_res_type=OrderBookTickerReturn,
        signed=False
    )

    NEW_ORDER = EndPoint(
        method="order.place",
        param_type=NewOrderParams,
        return_res_type=NewOrderReturn,
        signed=True
    )

    MODIFY_ORDER = EndPoint(
        method="order.modify",
        param_type=ModifyOrderParams,
        return_res_type=ModifyOrderReturn,
        signed=True
    )

    CANCEL_ORDER = EndPoint(
        method="order.cancel",
        param_type=CancelOrderParams,
        return_res_type=CancelOrderReturn,
        signed=True
    )

    QUERY_ORDER = EndPoint(
        method="order.status",
        param_type=QueryOrderParams,
        return_res_type=QueryOrderReturn,
        signed=True
    )

    ACCOUNT_BALANCE = EndPoint(
        method="v2/account.balance",
        param_type=NoParams,
        return_res_type=AccountBalanceReturn,
        signed=True
    )

    