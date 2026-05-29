from __future__ import annotations
from pydantic import RootModel, Field, field_validator
from typing import TypedDict, Generic, TypeVar, Type, Optional, Literal, Union, Annotated, Any, List
from enum import Enum
from decimal import Decimal
import pandas as pd

from ...constants import (
    Symbol, CandleInterval, ContractType, RequestMethod, OrderType, TimeInForce,
    OrderSide, PositionSide, PriceMatch, MarginType, Bool
)
from ..api_return_schema import (
    SymbolPriceTickerReturn, OrderBookTickerReturn, NewOrderReturn, ModifyOrderReturn,
    MyBaseModel, CancelOrderReturn, QueryOrderReturn, AccountBalanceReturn
)

P = TypeVar("P") # Parameter Type
R = TypeVar("R", bound=MyBaseModel|RootModel) # Return Type

# ---- params ----
class NoParams(TypedDict):...

class AutoCancelOrderParams(TypedDict):
    symbol:Symbol
    countdownTime:int

class CancelAllOrderParams(TypedDict):
    symbol:Symbol

class ModifyOrderParams(TypedDict):
    orderId:Optional[int]=None
    origClientOrderId:Optional[str]=None
    symbol:Symbol
    side:OrderSide
    quantity:Decimal
    price:Optional[Decimal]=None
    priceMatch:Optional[PriceMatch]=None

class ContKlineParams(TypedDict):
    pair:Symbol
    interval:CandleInterval
    contractType:ContractType
    startTime:Optional[int]=None
    endTime: Optional[int]=None
    limit: Optional[int]=None

class SymbolPriceTickerParams(TypedDict):
    symbol:Symbol

class OrderBookTickerParams(TypedDict):
    symbol:Symbol

class NewOrderParams(TypedDict):
    symbol:Symbol
    side:OrderSide
    positionSide:Optional[PositionSide] = None
    type:OrderType
    timeInForce:Optional[TimeInForce] = None
    quantity:Optional[Decimal] = None
    reduceOnly:Optional[str] = None
    price:Optional[Decimal] = None
    newClientOrderId:Optional[str] = None
    newOrderRespType:Optional[str] = None
    priceMatch:Optional[PriceMatch] = None
    selfTradePreventionMode:Optional[str] = None
    goodTillDate:Optional[int] = None

class CancelOrderParams(TypedDict):
    symbol:Symbol
    orderId:Optional[int]=None
    origClientOrderId:Optional[str]=None

class QueryOrderParams(TypedDict):
    symbol:Symbol
    orderId:Optional[int]
    origClientOrderId:Optional[str]

class ChangeMarginTypeParams(TypedDict):
    symbol:Symbol
    margintype:MarginType # wtf no cap for param name

class ChangePositionModeParams(TypedDict):
    dualSidePosition:Bool

class ChangeLeverageParams(TypedDict):
    symbol:Symbol
    leverage:int

class ChangeMultiAssetsModeParams(TypedDict):
    multiAssetsMargin:Bool

class SymbolConfigParams(TypedDict):
    symbol:Symbol

class PositionInfoParams(TypedDict):
    Symbol:Symbol

# ---- return value ----
class RawReturn(MyBaseModel):
    code:int
    msg:str

class AutoCancelOrderReturn(MyBaseModel):
    symbol:Symbol
    countdownTime:Decimal

class ServerTimeReturn(MyBaseModel):
    server_time:int=Field(alias="serverTime")

class ContKlineReturn(RootModel):
    # The 'root' is a list of lists (the raw Binance response)
    root:List[List[Any]]

    @field_validator("root", mode="after")
    @classmethod
    def to_dataframe(cls, v: List[List[Any]]) -> pd.DataFrame:
        # Define the standard Binance Kline columns
        columns = [
            "open_time", "open_price", "high_price", "low_price", "close_price", 
            "volume", "close_time", "quote_asset_volume", "trade_num",
            "taker_buy_volume", "taker_buy_quote_asset_volume", "ignore"
        ]
        
        df = pd.DataFrame(v, columns=columns)
        
        # Convert numeric columns from strings to floats
        decimal_cols = [
            "open_price", "high_price", "low_price", "close_price", 
            "volume", "quote_asset_volume", "taker_buy_volume", "taker_buy_quote_asset_volume"]
        for col in decimal_cols:
            df[col] = df[col].apply(Decimal)
            
        return df

    # This allows you to call .dataframe on the object easily
    @property
    def df(self) -> pd.DataFrame:
        return self.root

class ChangeLeverageReturn(MyBaseModel):
    leverage:int
    max_notional_value:Decimal=Field(alias="maxNotionalValue")
    symbol:Symbol

class AccountConfigReturn(MyBaseModel):
    fee_tier:int=Field(alias="feeTier")
    can_trade:bool=Field(alias="canTrade")
    can_deposit:bool=Field(alias="canDeposit")
    can_withdraw:bool=Field(alias="canWithdraw")
    dual_side_position:bool=Field(alias="dualSidePosition")
    update_time:int=Field(alias="updateTime")
    multi_assets_margin:bool=Field(alias="multiAssetsMargin")
    trade_group_id:int=Field(alias="tradeGroupId")

class _SymbolItem(MyBaseModel):
    symbol:Symbol
    margin_type:MarginType=Field(alias="marginType")
    is_auto_add_margin:bool=Field(alias="isAutoAddMargin")
    leverage:int
    max_notional_value:Decimal=Field(alias="maxNotionalValue")

# tf??? the only endpoint that always return list even in single symbol???
class SymbolConfigReturn(RootModel):
    root: List[_SymbolItem]

    def get_symbol(self, symbol:Symbol) -> _SymbolItem|None:
        """Finds a balance item by its asset name (e.g., 'USDT')."""
        return next((item for item in self.root if item.asset == symbol), None)

    def __iter__(self):
        return iter(self.root)
    
    def __getitem__(self, item)->_SymbolItem:
        return self.root[item]

class _PositionItem(MyBaseModel):
    symbol:Symbol
    position_side:PositionSide=Field(alias="positionSide")
    position_amt:Decimal=Field(alias="positionAmt")
    entry_price:Decimal=Field(alias="entryPrice")
    break_even_price:Decimal=Field(alias="breakEvenPrice")
    mark_price:Decimal=Field(alias="markPrice")
    un_realized_profit:Decimal=Field(alias="unRealizedProfit")
    liquidation_price:Decimal=Field(alias="liquidationPrice")
    isolated_margin:Decimal=Field(alias="isolatedMargin")
    notional:Decimal
    margin_asset:str=Field(alias="marginAsset")
    isolated_wallet:Decimal=Field(alias="isolatedWallet")
    initial_margin:Decimal=Field(alias="initialMargin")
    maint_margin:Decimal=Field(alias="maintMargin")
    position_initial_margin:Decimal=Field(alias="positionInitialMargin")
    open_order_initial_argin:Decimal=Field(alias="openOrderInitialMargin")
    adl:int
    bid_notional:Decimal=Field(alias="bidNotional")
    ask_notional:Decimal=Field(alias="askNotional")
    update_time:int=Field(alias="updateTime")

class PositionInfoReturn(RootModel):
    root:List[_PositionItem]

    def get_position(self, symbol:Symbol, position_side:PositionSide):
        return next((item for item in self.root if item.symbol==symbol and item.position_side==position_side), None)

    def __iter__(self):
        return iter(self.root)
    
    def __getitem__(self, item)->_PositionItem:
        return self.root[item]
    
# exchange info
class _RateLimit(MyBaseModel):
    rate_limit_type:str=Field(alias="rateLimitType")
    interval:str
    interval_num:int=Field(alias="intervalNum")
    limit:int

class _Asset(MyBaseModel):
    asset:str
    margin_available:bool=Field(alias="marginAvailable")
    auto_asset_exchange:Decimal=Field(alias="autoAssetExchange")

class _PriceFilter(MyBaseModel):
    filter_type: Literal["PRICE_FILTER"] = Field(alias="filterType")
    min_price: Decimal = Field(alias="minPrice")
    max_price: Decimal = Field(alias="maxPrice")
    tick_size: Decimal = Field(alias="tickSize")
    
class _LotSizeFilter(MyBaseModel):
    filter_type: Literal["LOT_SIZE"] = Field(alias="filterType")
    min_qty: Decimal = Field(alias="minQty")
    max_qty: Decimal = Field(alias="maxQty")
    step_size: Decimal = Field(alias="stepSize")

class _MarketLotSizeFilter(MyBaseModel):
    filter_type: Literal["MARKET_LOT_SIZE"] = Field(alias="filterType")
    min_qty:Decimal = Field(alias="minQty")
    max_qty:Decimal = Field(alias="maxQty")
    step_size:Decimal = Field(alias="stepSize")

class _MaxNumOrderFilter(MyBaseModel):
    filter_type: Literal["MAX_NUM_ORDERS"] = Field(alias="filterType")
    limit:int

class _MaxNumAlgoOrderFilter(MyBaseModel):
    filter_type: Literal["MAX_NUM_ALGO_ORDERS"] = Field(alias="filterType")
    limit:int

class _MinNotionalFilter(MyBaseModel):
    filter_type: Literal["MIN_NOTIONAL"] = Field(alias="filterType")
    notional:Decimal

class _PercentPriceFilter(MyBaseModel):
    filter_type: Literal["PERCENT_PRICE"] = Field(alias="filterType")
    multiplier_up: Decimal = Field(alias="multiplierUp")
    multiplier_decimal:Decimal = Field(alias="multiplierDecimal")
    multiplier_down: Decimal = Field(alias="multiplierDown")

class _PositionRiskControlFilter(MyBaseModel):
    filter_type: Literal["POSITION_RISK_CONTROL"] = Field(alias="filterType")
    position_control_side:str = Field(alias="positionControlSide")

BinanceFilter = Annotated[
    Union[
        _PriceFilter, 
        _LotSizeFilter, 
        _MarketLotSizeFilter, 
        _MaxNumOrderFilter,
        _MaxNumAlgoOrderFilter,
        _MinNotionalFilter,  
        _PercentPriceFilter,
        _PositionRiskControlFilter
    ],
    Field(discriminator="filter_type") # This points to the field with Literal
]

class _Symbols(MyBaseModel):
    symbol:str
    pair:str
    contractType:ContractType
    deliveryDate:int
    onboardDate:int
    status:str
    maintMarginPercent:Decimal
    requiredMarginPercent:Decimal
    baseAsset:str
    quoteAsset:str
    marginAsset:str
    pricePrecision:int
    quantityPrecision:int
    baseAssetPrecision:int
    quotePrecision:int
    underlyingType:str
    underlyingSubType:list
    triggerProtect:Decimal
    liquidationFee:Decimal
    marketTakeBound:Decimal
    maxMoveOrderLimit:int
    filters:list[BinanceFilter]
    orderTypes:list[OrderType]
    timeInForce:list[TimeInForce]
    permissionSets:list

    @property
    def price_filter(self)->_PriceFilter|None:
        return next((f for f in self.filters if isinstance(f, _PriceFilter)), None)

    @property
    def lot_size(self)->_LotSizeFilter|None:
        return next((f for f in self.filters if isinstance(f, _LotSizeFilter)), None)

    @property
    def market_lot_size(self)->_MarketLotSizeFilter|None:
        return next((f for f in self.filters if isinstance(f, _MarketLotSizeFilter)), None)
    
    @property
    def max_num_order(self)->_MaxNumOrderFilter|None:
        return next((f for f in self.filters if isinstance(f, _MaxNumOrderFilter)), None)
    
    @property
    def max_num_algo_order(self)->_MaxNumAlgoOrderFilter|None:
        return next((f for f in self.filters if isinstance(f, _MaxNumAlgoOrderFilter)), None)

    @property
    def min_notional(self)->_MinNotionalFilter|None:
        return next((f for f in self.filters if isinstance(f, _MinNotionalFilter)), None)
    
    @property
    def percent_price_filter(self)->_PercentPriceFilter|None:
        return next((f for f in self.filters if isinstance(f, _PercentPriceFilter)), None)

    @property
    def Position_risk_control(self)->_PositionRiskControlFilter|None:
        return next((f for f in self.filters if isinstance(f, _PercentPriceFilter)), None)

class ExchangeInfoReturn(MyBaseModel):
    exchange_filter:list=Field(alias="exchangeFilters")
    timezone:str
    serverTime:int
    futuresType:str
    rateLimits:list[_RateLimit]
    assets:list[_Asset]
    symbols:list[_Symbols]
    
# ---- api ----
class EndPoint(MyBaseModel, Generic[P, R]):
    method:RequestMethod
    name:str
    param_type:Type[P] 
    signed:bool
    return_type:Type[R]

class RestEndpointCollection(Enum):
    SERVER_TIME = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/time",
        param_type=NoParams,
        return_type=ServerTimeReturn,
        signed=False,
    )

    EXCHANGE_INFO = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/exchangeInfo",
        param_type=NoParams,
        return_type=ExchangeInfoReturn,
        signed=False,
    )

    CONT_KLINE = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/continuousKlines",
        param_type=ContKlineParams,
        return_type=ContKlineReturn,
        signed=False,
    )

    ORDER_BOOK_TICKER = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/ticker/bookTicker",
        param_type=OrderBookTickerParams,
        return_type=OrderBookTickerReturn,
        signed=False
    )

    SYMBOL_PRICE_TICKER = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v2/ticker/price",
        param_type=SymbolPriceTickerParams,
        return_type=SymbolPriceTickerReturn,
        signed=False
    )

    NEW_ORDER = EndPoint(
        method=RequestMethod.POST,
        name="/fapi/v1/order",
        param_type=NewOrderParams,
        return_type=NewOrderReturn,
        signed=True
    )

    CANCEL_ORDER = EndPoint(
        method=RequestMethod.DELETE,
        name="/fapi/v1/order",
        param_type=CancelOrderParams,
        return_type=CancelOrderReturn,
        signed=True
    )

    QUERY_ORDER = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/order",
        param_type=QueryOrderParams,
        return_type=QueryOrderReturn,
        signed=True
    )

    MODIFY_ORDER = EndPoint(
        method=RequestMethod.PUT,
        name="/fapi/v1/order",
        param_type=ModifyOrderParams,
        return_type=ModifyOrderReturn,
        signed=True
    )

    CHANGE_MARGIN_TYPE = EndPoint(
        method=RequestMethod.POST,
        name="/fapi/v1/marginType",
        param_type=ChangeMarginTypeParams,
        return_type=RawReturn,
        signed=True
    )

    # need no exist order to change
    CHANGE_POSITION_MODE = EndPoint( 
        method=RequestMethod.POST,
        name="/fapi/v1/positionSide/dual",
        param_type=ChangePositionModeParams,
        return_type=RawReturn,
        signed=True
    )

    CHANGE_LEVERAGE = EndPoint(
        method=RequestMethod.POST,
        name="/fapi/v1/leverage",
        param_type=ChangeLeverageParams,
        return_type=ChangeLeverageReturn,
        signed=True
    )

    CHANGE_MULTI_ASSETS_MODE = EndPoint(
        method=RequestMethod.POST,
        name="/fapi/v1/multiAssetsMargin",
        param_type=ChangeMultiAssetsModeParams,
        return_type=RawReturn,
        signed=True
    )

    ACCOUNT_BALANCE = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v3/balance",
        param_type=NoParams,
        return_type=AccountBalanceReturn,
        signed=True
    )

    ACCOUNT_CONFIG = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/accountConfig",
        param_type=NoParams,
        return_type=AccountConfigReturn,
        signed=True
    )

    SYMBOL_CONFIG = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v1/symbolConfig",
        param_type=SymbolConfigParams,
        return_type=SymbolConfigReturn,
        signed=True
    )

    CANCEL_ALL_ORDER = EndPoint(
        method=RequestMethod.DELETE,
        name="/fapi/v1/allOpenOrders",
        param_type=CancelAllOrderParams,
        return_type=RawReturn,
        signed=True
    )

    AUTO_CANCEL_ORDER = EndPoint(
        method=RequestMethod.POST,
        name="/fapi/v1/countdownCancelAll",
        param_type=AutoCancelOrderParams,
        return_type=AutoCancelOrderReturn,
        signed=True
    )

    POSITION_INFO = EndPoint(
        method=RequestMethod.GET,
        name="/fapi/v3/positionRisk",
        param_type=PositionInfoParams,
        return_type=PositionInfoReturn,
        signed=True
    )