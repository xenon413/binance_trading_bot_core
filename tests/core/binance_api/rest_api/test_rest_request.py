import pytest
from unittest.mock import MagicMock, call
import time
from decimal import Decimal

from core.binance_api.rest_api.rest_api import BinanceRestapi
from core.binance_api.rest_api.rest_api_schema import (
    RestEndpointCollection, EndPoint, P, R
)
from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)
from core.exceptions import BotError

# test one get market data (standard endpoint)
@pytest.mark.precheck
def test_get_server_time(rest_api_handle:BinanceRestapi):
    rest_api_handle.request(RestEndpointCollection.SERVER_TIME.value)
    
# test one standard trade process (and secure endpoint)
@pytest.mark.precheck
@pytest.mark.fixme
def test_order_lifecycle1(rest_api_handle:BinanceRestapi):
    '''
    lifesycle: limit order -> modify*2 -> query -> cancel -> query
    '''

    order_endpoint = RestEndpointCollection.NEW_ORDER.value
    cancel_endpoint = RestEndpointCollection.CANCEL_ORDER.value
    query_endpoint = RestEndpointCollection.QUERY_ORDER.value
    modify_endpoint = RestEndpointCollection.MODIFY_ORDER.value

    # creating new limit order
    res = rest_api_handle.request(
        order_endpoint,
        {
            "symbol":Symbol.BTCUSDC, 
            "priceMatch":PriceMatch.QUEUE_20, 
            "quantity":0.005,
            "side":OrderSide.BUY,
            "positionSide":PositionSide.LONG,
            "timeInForce":TimeInForce.GTX,
            "type":OrderType.LIMIT
        }
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 1
    res = rest_api_handle.request(
        modify_endpoint,
        {
            "orderId":res.order_id, 
            "symbol":Symbol.BTCUSDC, 
            "side":OrderSide.BUY, 
            "price":res.price, 
            "quantity":0.006
        }
    )

    # validate
    assert res.orig_qty == Decimal("0.006"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 2
    res = rest_api_handle.request(
        modify_endpoint,
        {
            "orderId":res.order_id, 
            "symbol":Symbol.BTCUSDC, 
            "side":OrderSide.BUY, 
            "priceMatch":PriceMatch.QUEUE_20, 
            "quantity":0.007
        }
    )

    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # query order
    res = rest_api_handle.request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },

    )

    # validate order
    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # cancel order
    res = rest_api_handle.request(
        cancel_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        }
    )

    # validate order
    assert res.order_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # query order
    res = rest_api_handle.request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
    )

    # validate order
    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

@pytest.mark.precheck
def test_cancel_reject_error(rest_api_handle:BinanceRestapi):
    res = rest_api_handle.request(RestEndpointCollection.CANCEL_ORDER.value, {"symbol":Symbol.BTCUSDC, "orderId":0})
    assert isinstance(res, BotError), f"return type error: {res}"
    print(res.message)
    # all of the print returns true
    # print(type(res)==BotError, type(res) is BotError, isinstance(res, BotError))

### test invalide requests error handle
# def test_xxx_error(rest_api_handle:BinanceRestapi, monkeypatch):
#     mock_sleep = MagicMock()
#     monkeypatch.setattr(time, "sleep", mock_sleep)
#     rest_api_handle.request()
#     assert mock_sleep.call_args_list == [call(5), call(10)]