import pytest
from websocket import create_connection
import json
import time
import os
import hashlib
import hmac
from pydantic import TypeAdapter
from decimal import Decimal

from core.binance_api.ws_api.ws_api_schema import (
    EndPoint, P, R, WSEndpointCollection, ReturnSchema
)
from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)

URL = "wss://testnet.binancefuture.com/ws-fapi/v1"

def timestamp(offset:int=0)->int:
    '''
    Params
        offset: in milliseconds
    '''
    return int(time.time()*1000+offset) # 13 dig timestamp

@pytest.fixture
def ws_connection():
    try:
        ws = create_connection(URL, timeout=5)
        yield ws
    finally:
        ws.close()

def ws_send(endpoint:EndPoint[P, R], param:P ,ws, key:str, secret:str)->ReturnSchema[R]:
    param:dict = {k:v for k,v in dict(param).items() if v is not None}
    
    if endpoint.signed:
        param |= {"apiKey":key, "timestamp":timestamp()}
        # config query for signature
        lst = [f"{k}={v}" for k, v in param.items()]
        lst.sort()
        query = "&".join(lst)

        # add sign to query
        signature = hmac.new(
            secret.encode("utf-8"), 
            query.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        param |= {"signature":signature}
    payload = {
        "id":str(int(time.time()*1000)),
        "method":endpoint.method,
        "params":param
    }
    
    ws.send(json.dumps(TypeAdapter(dict).dump_python(payload, mode="json")))
    res = json.loads(ws.recv())
    print(res)
    return endpoint.return_type.model_validate(res)

def test_get_symbol_price_ticker(ws_connection, api_credentials):
    endpoint = WSEndpointCollection.SYMBOL_PRICE_TICKER.value
    ws_send(endpoint, {"symbol":Symbol.BTCUSDC}, ws_connection, **api_credentials)

def test_get_order_book_ticker(ws_connection, api_credentials):
    endpoint = WSEndpointCollection.ORDER_BOOK_TICKER.value
    ws_send(endpoint, {"symbol":Symbol.BTCUSDC}, ws_connection, **api_credentials)

def test_get_account_balance(ws_connection, api_credentials):
    endpoint = WSEndpointCollection.ACCOUNT_BALANCE.value
    ws_send(endpoint, {}, ws_connection, **api_credentials)

def test_order_lifecycle1(ws_connection, api_credentials):
    '''
    lifesycle: limit order -> modify*2 -> query -> cancel -> query
    '''
    order_endpoint = WSEndpointCollection.NEW_ORDER.value
    modify_endpoint = WSEndpointCollection.MODIFY_ORDER.value
    query_endpoint = WSEndpointCollection.QUERY_ORDER.value
    cancel_endpoint = WSEndpointCollection.CANCEL_ORDER.value

    # order
    res = ws_send(
        order_endpoint, 
        {
            "symbol":Symbol.BTCUSDC,
            "priceMatch":PriceMatch.QUEUE_20,
            "quantity":0.005,
            "side":OrderSide.BUY,
            "positionSide":PositionSide.LONG,
            "timeInForce":TimeInForce.GTX,
            "type":OrderType.LIMIT
        },
        ws_connection, 
        **api_credentials
    )

    # validate 
    assert res.result.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # modify 1
    res = ws_send(modify_endpoint, {"orderId":res.result.order_id, "price":res.result.price, "quantity":0.006, "symbol":Symbol.BTCUSDC, "side":OrderSide.BUY}, ws_connection, **api_credentials)
    
    # validate
    assert res.result.orig_qty == Decimal("0.006"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
       
    # modify 2
    res = ws_send(modify_endpoint, {"orderId":res.result.order_id, "symbol":Symbol.BTCUSDC, "side":OrderSide.BUY, "priceMatch":PriceMatch.QUEUE_20, "quantity":0.007}, ws_connection, **api_credentials)
    
    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # query
    res = ws_send(query_endpoint, {"symbol":Symbol.BTCUSDC, "orderId":res.result.order_id}, ws_connection, **api_credentials)
    
    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.NEW, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # cancel
    res = ws_send(cancel_endpoint, {"symbol":Symbol.BTCUSDC, "orderId":res.result.order_id}, ws_connection, **api_credentials)
    
    assert res.result.order_qty == Decimal("0.007"), f"order quantity miss match: {res.result.order_qty}"
    assert res.result.status == OrderStatus.CANCELED, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
    # query
    res = ws_send(query_endpoint, {"symbol":Symbol.BTCUSDC, "orderId":res.result.order_id}, ws_connection, **api_credentials)

    assert res.result.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.result.orig_qty}"
    assert res.result.status == OrderStatus.CANCELED, f"order status miss match: {res.result.status}"
    assert res.result.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.result.symbol}"
    assert res.result.side == OrderSide.BUY, f"order side miss match: {res.result.side}"
    assert res.result.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.result.time_in_force}"
    assert res.result.orig_type == OrderType.LIMIT, f"order type miss match: {res.result.orig_type}"
    
### get error response and write error handle for ws send