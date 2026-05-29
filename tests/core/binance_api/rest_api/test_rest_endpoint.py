import requests
import hashlib
import hmac
import json
import time
from decimal import Decimal
import pandas as pd
import pytest


from core.binance_api.rest_api.rest_api_schema import (
    RestEndpointCollection, EndPoint, P, R
)
from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)

URL="https://testnet.binancefuture.com"

def timestamp(offset:int=0)->int:
    '''
    Params
        offset: in milliseconds
    '''
    return int(time.time()*1000+offset) # 13 dig timestamp

def request(endpoint: EndPoint[P, R], param: P, key:str, secret:str) -> R:
    payload = dict(param)

    # add param for signed
    if endpoint.signed:
        payload |= {"timestamp": timestamp()}

    # config query
    query = "&".join([f"{k}={v}" for k, v in payload.items() if v is not None])

    # add sign to query
    if endpoint.signed:
        signature = hmac.new(
            secret.encode("utf-8"), 
            query.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()
        query += f"&signature={signature}"

    # construct full url
    full_url = f"{URL}{endpoint.name}?{query}"

    # actual request
    r = requests.request(endpoint.method, full_url, headers={"X-MBX-APIKEY":key})


    res:dict|list = json.loads(r.text)

    # some endpoint return code=200, msg="success"
    if isinstance(res, dict) and res.get("code", 200) != 200:
        assert False, res

    # validate with endpoint
    return endpoint.return_type.model_validate(res)

# test success
def test_get_server_time(api_credentials):
    endpoint = RestEndpointCollection.SERVER_TIME.value
    request(endpoint, {}, **api_credentials)

@pytest.mark.precheck
def test_get_exchange_info(api_credentials):
    endpoint = RestEndpointCollection.EXCHANGE_INFO.value
    request(endpoint, {}, **api_credentials)

@pytest.mark.precheck
def test_get_cont_kline(api_credentials):
    endpoint = RestEndpointCollection.CONT_KLINE.value
    res = request(
        endpoint, 
        {
            "pair":Symbol.BTCUSDC, 
            "contractType":ContractType.PERPETUAL,
            "limit":1,
            "interval":CandleInterval.MIN_1,
        },
         **api_credentials
    )
    assert isinstance(res.df, pd.DataFrame), f"fail to get df cur type:{type(res.df)}"
    columns = {
        "open_time", "open_price", "high_price", "low_price", "close_price", 
        "volume", "close_time", "quote_asset_volume", "trade_num",
        "taker_buy_volume", "taker_buy_quote_asset_volume", "ignore"
    }
    assert set(res.df.columns) == columns, f"df column doesn't match"

@pytest.mark.precheck
def test_get_order_book_ticker(api_credentials):
    endpoint = RestEndpointCollection.ORDER_BOOK_TICKER.value
    request(endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)

@pytest.mark.precheck
def test_get_symbol_price_ticker(api_credentials):
    endpoint = RestEndpointCollection.SYMBOL_PRICE_TICKER.value
    request(endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)

@pytest.mark.precheck
def test_get_account_balance(api_credentials):
    endpoint = RestEndpointCollection.ACCOUNT_BALANCE.value
    res = request(endpoint,{},**api_credentials)

    # test iter
    for i in res:
        pass
    
    assert res.get_asset("USDC"), "can't get USDC balance"

@pytest.mark.precheck
def test_get_account_config(api_credentials):
    endpoint = RestEndpointCollection.ACCOUNT_CONFIG.value
    request(endpoint, {}, **api_credentials)

@pytest.mark.precheck
def test_get_symbol_config(api_credentials):
    endpoint = RestEndpointCollection.SYMBOL_CONFIG.value
    request(endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)

@pytest.mark.precheck
def test_get_position_info(api_credentials):
    endpoint = RestEndpointCollection.POSITION_INFO.value
    request(endpoint, {}, **api_credentials)
    request(endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)

def test_change_margin_settings(api_credentials):
    margin_type_endpoint = RestEndpointCollection.CHANGE_MARGIN_TYPE.value
    multi_assets_endpoint = RestEndpointCollection.CHANGE_MULTI_ASSETS_MODE.value
    ### currently assume that initial margin type is isolated
    request(margin_type_endpoint, {"symbol":Symbol.BTCUSDC, "margintype":MarginType.CROSSED}, **api_credentials)
    
    # the fucking lag on change 
    # time.sleep(5)
    # could only change to mullti assets under cross marign type, need to change all margin type not just one
    request(multi_assets_endpoint, {"multiAssetsMargin":True}, **api_credentials)
    request(multi_assets_endpoint, {"multiAssetsMargin":False}, **api_credentials)

    # reset back to original margin type
    request(margin_type_endpoint, {"symbol":Symbol.BTCUSDC, "margintype":MarginType.ISOLATED}, **api_credentials)

def test_change_position_mode(api_credentials):
    endpoint = RestEndpointCollection.CHANGE_POSITION_MODE.value

    ### assume that initial position mode is on dual
    request(endpoint, {"dualSidePosition":False}, **api_credentials)

    # reset back to original position mode
    request(endpoint, {"dualSidePosition":True}, **api_credentials)

@pytest.mark.precheck
def test_change_leverage(api_credentials):
    endpoint = RestEndpointCollection.CHANGE_LEVERAGE.value
    request(endpoint, {"symbol":Symbol.BTCUSDC, "leverage":10}, **api_credentials)
    request(endpoint, {"symbol":Symbol.BTCUSDC, "leverage":1}, **api_credentials)

@pytest.mark.precheck
@pytest.mark.fixme
def test_order_lifecycle1(api_credentials):
    '''
    lifecycle: limit order -> query -> cancel -> query
    '''
    order_endpoint = RestEndpointCollection.NEW_ORDER.value
    query_endpoint = RestEndpointCollection.QUERY_ORDER.value
    cancel_endpoint = RestEndpointCollection.CANCEL_ORDER.value

    # creating new limit order queue_20 so it stays on the book
    res = request(
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
        **api_credentials
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # query order
    res = request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
        **api_credentials
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # cancel order
    res = request(
        cancel_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
        **api_credentials
    )

    # validate order
    assert res.order_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # query order
    res = request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
        **api_credentials
    )
    
    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

@pytest.mark.precheck
@pytest.mark.fixme
def test_order_lifecycle2(api_credentials):
    '''
    lifecycle: limit -> modify*2 -> auto cancel -> query
    '''

    auto_cancel_endpoint = RestEndpointCollection.AUTO_CANCEL_ORDER.value
    order_endpoint = RestEndpointCollection.NEW_ORDER.value
    query_endpoint = RestEndpointCollection.QUERY_ORDER.value
    modoify_endpoint = RestEndpointCollection.MODIFY_ORDER.value

    res = request(
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
        **api_credentials
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 1
    res = request(modoify_endpoint, {"orderId":res.order_id, "symbol":Symbol.BTCUSDC, "side":OrderSide.BUY, "price":res.price, "quantity":0.006}, **api_credentials)
    
    # validate order
    assert res.orig_qty == Decimal("0.006"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 2
    res = request(modoify_endpoint, {"orderId":res.order_id, "symbol":Symbol.BTCUSDC, "side":OrderSide.BUY, "priceMatch":PriceMatch.QUEUE_20, "quantity":0.007}, **api_credentials)
    
    # validate order
    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # use as cancel order
    request(auto_cancel_endpoint, {"symbol":Symbol.BTCUSDC, "countdownTime":1}, **api_credentials)

    # query order
    res = request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
        **api_credentials
    )
    # validate order
    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

@pytest.mark.precheck
@pytest.mark.fixme
def test_order_lifecycle3(api_credentials):
    '''
    lifecycle: limit order -> cancel all -> query
    '''

    cancel_all_endpoint = RestEndpointCollection.CANCEL_ALL_ORDER.value
    order_endpoint = RestEndpointCollection.NEW_ORDER.value
    query_endpoint = RestEndpointCollection.QUERY_ORDER.value

    # cancel with no order open
    request(cancel_all_endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)

    res = request(
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
        **api_credentials
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # cancel order
    request(cancel_all_endpoint, {"symbol":Symbol.BTCUSDC}, **api_credentials)


    # query order
    res = request(
        query_endpoint,
        {
            "orderId":res.order_id,
            "symbol":res.symbol
        },
        **api_credentials
    )

    # validate order
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

