from ..constants import (
    Symbol, OrderSide, OrderStatus, OrderType, PositionSide, TimeInForce,
    PriceMatch
)
from decimal import Decimal
from pydantic import Field, RootModel
from typing import List
from ..my_base_model import MyBaseModel


class SymbolPriceTickerReturn(MyBaseModel):
    '''rest/ws'''
    symbol:Symbol
    price:Decimal
    trans_time:int=Field(alias="time")

class OrderBookTickerReturn(MyBaseModel):
    '''rest/ws'''
    last_update_id:int=Field(None, alias="lastUpdateId") # not on the rest doc example output but actually in it
    symbol:Symbol
    bid_price:Decimal=Field(alias="bidPrice")
    bid_qty:Decimal=Field(alias="bidQty")
    ask_price:Decimal=Field(alias="askPrice")
    ask_qty:Decimal=Field(alias="askQty")
    trans_time:int=Field(alias="time")

class NewOrderReturn(MyBaseModel):
    '''rest/ws'''
    client_order_id:str=Field(alias="clientOrderId")
    cum_qty:Decimal=Field(alias="cumQty")
    cum_quote:Decimal=Field(alias="cumQuote")
    executed_qty:Decimal=Field(alias="executedQty")
    order_id:int=Field(alias="orderId")
    avg_price:Decimal=Field(alias="avgPrice")
    orig_qty:Decimal=Field(alias="origQty")
    price:Decimal
    reduce_only:bool=Field(alias="reduceOnly")
    side:OrderSide
    position_side:PositionSide=Field(alias="positionSide")
    status:OrderStatus
    stop_price:Decimal=Field(alias="stopPrice")
    close_position:bool=Field(alias="closePosition") # if close all
    symbol:Symbol
    time_in_force:TimeInForce=Field(alias="timeInForce")
    type:OrderType
    orig_type:OrderType=Field(alias="origType")
    update_time:int=Field(alias="updateTime")
    working_type:str=Field(alias="workingType")
    price_protect:bool=Field(alias="priceProtect")
    price_match:str=Field(alias="priceMatch")
    self_trade_prevention_mode:str=Field(alias="selfTradePreventionMode")
    good_till_date:int=Field(alias="goodTillDate")

### integrate with new order return and query order return
class ModifyOrderReturn(MyBaseModel):
    '''rest/ws'''
    order_id:int=Field(alias="orderId")
    symbol:Symbol 
    # pair:Symbol #???? whyyyyyyyy symbol and pair the same thing, ohhh it only exist in the rest doc got fucking scammed
    status:OrderStatus 
    client_order_id:str=Field(alias="clientOrderId")
    price:Decimal
    avg_price:Decimal=Field(alias="avgPrice")
    orig_qty:Decimal=Field(alias="origQty")
    executed_qty:Decimal=Field(alias="executedQty")
    cum_qty:Decimal=Field(alias="cumQty")
    cum_quote:Decimal=Field(None, alias="cumQuote") # rest doc use cumBase but actually return cumQuote
    # cum_base:Decimal=Field(alias="cumBase") also got fucking scammed by doc in rest
    time_in_force:TimeInForce=Field(alias="timeInForce")
    type:OrderType
    reduce_only:bool=Field(alias="reduceOnly")
    close_position:bool=Field(alias="closePosition")
    side:OrderSide
    position_side:PositionSide=Field(alias="positionSide")
    stop_price:Decimal=Field(alias="stopPrice")
    working_type:str=Field(alias="workingType") # don't know tf this is
    price_protect:bool=Field(alias="priceProtect")
    orig_type:OrderType=Field(alias="origType")
    price_match:PriceMatch=Field(alias="priceMatch") # shit if not price match is "NONE" solve by adding NONE in price match class
    self_trade_prevention_mode:str=Field(alias="selfTradePreventionMode")
    good_till_date:int=Field(alias="goodTillDate")
    update_time:int=Field(alias="updateTime")

class CancelOrderReturn(MyBaseModel):
    '''rest/ws'''
    client_order_id:str=Field(alias="clientOrderId")
    cum_qty:Decimal=Field(alias="cumQty")
    cum_quote:Decimal=Field(alias="cumQuote")
    executed_qty:Decimal=Field(alias="executedQty")
    order_id:int=Field(alias="orderId")
    order_qty:Decimal=Field(alias="origQty")
    orig_type:OrderType=Field(alias="origType")
    price:Decimal
    avg_price:Decimal=Field(alias="avgPrice") ### not in ws
    reduce_only:bool=Field(alias="reduceOnly")
    side:OrderSide
    position_side:PositionSide=Field(alias="positionSide")
    status:OrderStatus
    stop_price:Decimal=Field(alias="stopPrice")
    close_position:bool=Field(alias="closePosition")
    symbol:Symbol
    time_in_force:TimeInForce=Field(alias="timeInForce")
    type:OrderType
    update_time:int=Field(alias="updateTime")
    working_type:str=Field(alias="workingType")
    price_protect:bool=Field(alias="priceProtect")
    price_match:str=Field(alias="priceMatch")
    self_trade_prevention_mode:str=Field(alias="selfTradePreventionMode")
    good_till_date:int=Field(alias="goodTillDate")

class QueryOrderReturn(MyBaseModel):
    '''rest/ws'''
    avg_price:Decimal=Field(alias="avgPrice")
    client_order_id:str=Field(alias="clientOrderId")
    cum_quote:Decimal=Field(alias="cumQuote")
    executed_qty:Decimal=Field(alias="executedQty")
    order_id:int=Field(alias="orderId")
    orig_qty:Decimal=Field(alias="origQty")
    orig_type:OrderType=Field(alias="origType")
    price:Decimal
    reduce_only:bool=Field(alias="reduceOnly")
    side:OrderSide
    position_side:PositionSide=Field(alias="positionSide")
    status:OrderStatus
    stop_price:Decimal=Field(alias="stopPrice")
    close_position:bool=Field(alias="closePosition")
    symbol:Symbol
    time:int # order time
    time_in_force:TimeInForce=Field(alias="timeInForce")
    type:OrderType
    update_time:int=Field(alias="updateTime")
    working_type:str=Field(alias="workingType")
    price_protect:bool=Field(alias="priceProtect")
    #extra that's not in the example
    price_match:PriceMatch=Field(alias="priceMatch")
    self_trade_prevention_mode:str=Field(alias="selfTradePreventionMode")
    good_till_date:int=Field(alias="goodTillDate")

class _BalanceItem(MyBaseModel):
    account_alias:str=Field(alias="accountAlias")
    asset:str
    balance:Decimal
    cross_wallet_balance:Decimal=Field(alias="crossWalletBalance")
    cross_unrealized_profit:Decimal=Field(alias="crossUnPnl")
    available_balance:Decimal=Field(alias="availableBalance")
    max_withdraw_amount:Decimal=Field(alias="maxWithdrawAmount")
    margin_available:bool=Field(alias="marginAvailable")
    update_time:int=Field(alias="updateTime")

class AccountBalanceReturn(RootModel):
    '''rest/ws'''
    root: List[_BalanceItem]

    def get_asset(self, asset_name: str) -> _BalanceItem|None:
        """Finds a balance item by its asset name (e.g., 'USDT')."""
        return next((item for item in self.root if item.asset == asset_name.upper()), None)

    def __iter__(self):
        return iter(self.root)
    
    def __getitem__(self, item)->_BalanceItem:
        return self.root[item]
