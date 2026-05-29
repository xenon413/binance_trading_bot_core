import pytest
from decimal import Decimal

from core.binance_api.ws_api.ws_api import WSapi
from core.binance_api.ws_api.ws_api_schema import (
    EndPoint, P, R, WSEndpointCollection, ReturnSchema
)

from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)

@pytest.fixture
def ws_connection():
    try:
        ws = WSapi(True)
        yield ws

    finally:
        ws.close()

def test_get_symbol_price_ticker(ws_connection:WSapi):
    ws_connection.send(WSEndpointCollection.SYMBOL_PRICE_TICKER.value, {"symbol":Symbol.BTCUSDC})

def test_get_order_book_ticker(ws_connection:WSapi):
    ws_connection.send(WSEndpointCollection.ORDER_BOOK_TICKER.value, {"symbol":Symbol.BTCUSDC})

def test_get_account_balance(ws_connection:WSapi):
    ws_connection.send(WSEndpointCollection.ACCOUNT_BALANCE.value)

def test_order_lifecycle1(ws_connection:WSapi):
    '''
    lifesycle: limit order -> modify*2 -> query -> cancel -> query
    '''

    # order
    res = ws_connection.send(
        WSEndpointCollection.NEW_ORDER.value, 
        {
            "symbol":Symbol.BTCUSDC,
            "priceMatch":PriceMatch.QUEUE_20,
            "quantity":0.005,
            "side":OrderSide.BUY,
            "positionSide":PositionSide.LONG,
            "timeInForce":TimeInForce.GTX,
            "type":OrderType.LIMIT
        },
    )

    # validate 
    assert res.result.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # modify 1
    res = ws_connection.send(
        WSEndpointCollection.MODIFY_ORDER.value,
        {
            "orderId":res.result.order_id, 
            "symbol":Symbol.BTCUSDC, 
            "side":OrderSide.BUY, 
            "price":res.result.price, 
            "quantity":0.006
        }
    )

    # validate
    assert res.result.orig_qty == Decimal("0.006"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"

    # modify 2
    res = ws_connection.send(
        WSEndpointCollection.MODIFY_ORDER.value,
        {
            "orderId":res.result.order_id, 
            "symbol":Symbol.BTCUSDC, 
            "side":OrderSide.BUY, 
            "priceMatch":PriceMatch.QUEUE_20, 
            "quantity":0.007
        }
    )

    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # query
    res = ws_connection.send(
        WSEndpointCollection.QUERY_ORDER.value,
        {
            "symbol":Symbol.BTCUSDC, 
            "orderId":res.result.order_id
        }
    )

    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"

    # cancel
    res = ws_connection.send(
        WSEndpointCollection.CANCEL_ORDER.value,
        {"symbol":Symbol.BTCUSDC, "orderId":res.result.order_id}
    )

    assert res.result.order_qty == Decimal("0.007"), f"order quantity miss match: {res.result.order_qty}"
    assert res.result.status == OrderStatus.CANCELED, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"

    # query
    res = ws_connection.send(
        WSEndpointCollection.QUERY_ORDER.value,
        {
            "symbol":Symbol.BTCUSDC, 
            "orderId":res.result.order_id
        }
    )

    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.CANCELED, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    