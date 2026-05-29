import pytest
import time
import pandas as pd

from core.log_handle import LogHandle
from core.binance_api.ws_stream.market_stream import WSManager, WSKlineDF, WSFetch
from core.binance_api.ws_stream.market_stream_schema import StreamEndpointCollection
from core.binance_api.rest_api.rest_api import BinanceRestapi
from core.binance_api.rest_api.rest_api_schema import RestEndpointCollection
from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)


# to see if the data delay is cause by the update speed of binacne endpoint
# result: manager update speed very fast usually less than 1s and max 2s for 2min
def test_query_update_speed(manager:WSManager, test_logger:LogHandle):
    params = StreamEndpointCollection.ORDER_BOOK_TICKER.value.param_type(symbol=Symbol.BTCUSDC)
    buff = manager.add_route("queue", StreamEndpointCollection.ORDER_BOOK_TICKER.value, params)
    pre_time = None
    while True:
        if buff.pop() is not None:
            timestamp = time.perf_counter()

            # calc duration
            if pre_time is not None:
                duration = timestamp - pre_time
                test_logger.write_log(f"duration: {duration}s")

            pre_time = timestamp 

# TODO:　add route that use market endpoint in sampling mode
@pytest.mark.precheck
def test_manager_sampling(manager:WSManager):
    '''cont kline with sampling mode'''
    params = StreamEndpointCollection.CONT_KLINE.value.param_type(
        pair=Symbol.BTCUSDT,contractType=ContractType.PERPETUAL, interval=CandleInterval.MIN_1
    )
    buff = manager.add_route("sampling", StreamEndpointCollection.CONT_KLINE.value, params)

    # wait till max size (1)
    while not buff.is_max_size():
        time.sleep(1)

    # print(buff.is_max_size())
    assert buff.size() == 1, "buff size miss matched"
    assert isinstance(buff.pop(), StreamEndpointCollection.CONT_KLINE.value.return_type), "return type miss matched"
    assert buff.is_max_size(), "buff not max size"

    # test for value update
    data1 = buff.pop()
    time.sleep(5)
    data2 = buff.pop()
    assert data1 != data2, "data didn't update"

    # test for tiem validation
    data = buff.pop()
    assert data.valid, "data is not valid"
    
@pytest.mark.precheck
def test_manager_query(manager:WSManager):
    '''order book ticker with queue mode'''
    params = StreamEndpointCollection.ORDER_BOOK_TICKER.value.param_type(symbol=Symbol.BTCUSDC)
    buff = manager.add_route("queue", StreamEndpointCollection.ORDER_BOOK_TICKER.value, params)

    # wait till one
    while buff.size() == 0:
        time.sleep(1)

    data = buff.pop()
    assert data.valid, "data"
    # wait till max size (100)
    while not buff.is_max_size():
        print(f"{buff.size()}/100")
        time.sleep(1)

    assert buff.size() == 100, "buff size miss matched"
    assert isinstance(buff.pop(), StreamEndpointCollection.ORDER_BOOK_TICKER.value.return_type), "return type miss matched"

    data1 = buff.pop()
    data2 = buff.pop()
    assert data1 != data2, "data didn't update"

### there's records of failed fetch
# TODO: make the test resilience to data=None
@pytest.mark.precheck
def test_fetch(manager:WSManager):
    f = WSFetch(manager)

    # test get order book
    params = StreamEndpointCollection.ORDER_BOOK_TICKER.value.param_type(
        symbol=Symbol.BTCUSDC
    )
    for _ in range(10):
        data = f.get_data(StreamEndpointCollection.ORDER_BOOK_TICKER.value, params)
        assert data.valid, "data is not valid"
        assert isinstance(data, StreamEndpointCollection.ORDER_BOOK_TICKER.value.return_type), "return type miss matched"
        time.sleep(1)

    # test get cont kline 
    params = StreamEndpointCollection.CONT_KLINE.value.param_type(
        pair=Symbol.BTCUSDC,contractType=ContractType.PERPETUAL, interval=CandleInterval.MIN_1
    )
    for _ in range(10):
        data = f.get_data(StreamEndpointCollection.CONT_KLINE.value, params)
        assert data.valid, "data is not valid"
        assert isinstance(data, StreamEndpointCollection.CONT_KLINE.value.return_type), "return type miss matched"
        time.sleep(1)

    # test get price ticker
    params = StreamEndpointCollection.SYMBOL_PRICE_TICKER.value.param_type(
        pair=Symbol.BTCUSDC
    )
    for _ in range(10):
        data = f.get_data(StreamEndpointCollection.SYMBOL_PRICE_TICKER.value, params)
        assert data.valid, "data is not valid"
        assert isinstance(data, StreamEndpointCollection.CONT_KLINE.value.return_type), "return type miss matched"
        time.sleep(1)


def validate_df(df:pd.DataFrame)->bool:
    '''to validate single df'''
    # check obj type
    assert isinstance(df, pd.DataFrame), f"data mismatched: {type(df)}"

    # check len
    assert len(df) == 1500, f"data lenght mismatched: {len(df)}"

    # check fields
    fields = ["open_time","open_price","high_price","low_price","close_price","volume","close_time","quote_asset_volume","trade_num","taker_buy_volume","taker_buy_quote_asset_volume","ignore"]
    assert list(df.columns) == fields, f"fields mismatched: {df.columns}"

    # check gaps
    gap_ms = 60*1000
    assert (df['open_time'].diff().iloc[1:] == gap_ms).all(), "open time gap"
    assert (df['close_time'].diff().iloc[1:] == gap_ms).all(), "close time gap"
    assert ((df['close_time'] - df['open_time']) == 59_999).all(), "open close time mismatched"
    
### there's records of failed rotation
# TODO: test if it's fixed
# TODO: make the test resilience to data=None
@pytest.mark.fixme
@pytest.mark.precheck
def test_kline_df(manager:WSManager, rest_api_handle:BinanceRestapi):
    # create rest api manager
    k = WSKlineDF(manager, rest_api_handle)
    # to test listen mulit intervals 
    k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_3)
    
    # time.sleep(10)
    try:
        data = k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
        validate_df(data)

        while True:
            # update
            time.sleep(1)
            pre_data = data
            data = k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
            validate_df(data)
            # if switch to next kline
            if pre_data.iloc[-1]["open_time"] != data.iloc[-1]["open_time"]:
                # verify historical data except the one that just closed
                assert (pre_data.iloc[1:-1].reset_index(drop=True) == data.iloc[:1498].reset_index(drop=True)).all().all()
                
                # validate against REST API
                rest_res = rest_api_handle.request(
                    RestEndpointCollection.CONT_KLINE.value,
                    {"pair": Symbol.BTCUSDC, "interval": CandleInterval.MIN_1, "contractType": ContractType.PERPETUAL, "limit": 1500}
                )
                
                # The REST API is often cached and might be delayed by a few milliseconds.
                # This means rest_res.df might be misaligned by 1 kline compared to `data`.
                # We align them strictly by 'open_time' and compare only the finalized historical klines.
                active_open_time = data.iloc[-1]["open_time"]
                data_closed = data[data["open_time"] < active_open_time]
                rest_closed = rest_res.df[rest_res.df["open_time"] < active_open_time]
                
                common_times = set(data_closed["open_time"]).intersection(set(rest_closed["open_time"]))
                data_compare = data_closed[data_closed["open_time"].isin(common_times)].sort_values("open_time").reset_index(drop=True)
                rest_compare = rest_closed[rest_closed["open_time"].isin(common_times)].sort_values("open_time").reset_index(drop=True)
                
                assert len(data_compare) > 0, "No common klines found"
                
                # Check that every single value matches exactly
                diff = data_compare == rest_compare
                assert diff.all().all(), f"WS data does not match REST API data. Mismatched columns: {diff.columns[~diff.all()].tolist()}"
                
                break
            
            # not yet switch
            # same start/end time 
            assert (pre_data["open_time"] == data["open_time"]).all(), f"data open time mismatched"
            assert (pre_data["close_time"] == data["close_time"]).all(), f"data close time mismatched"

            pre_data = data

    except AssertionError as e:
        if data is not None:
            data.to_csv("data.csv", index=False)
        if pre_data is not None:
            pre_data.to_csv("pre_data.csv", index=False)
        raise

# @pytest.mark.fixme
def test_kline_df2(manager:WSManager, rest_api_handle:BinanceRestapi):
    # create rest api manager
    k = WSKlineDF(manager, rest_api_handle)
    k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
    time.sleep(300)
    data = k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
    data.to_csv("res.csv", index=False)

def test_kline_df3(manager:WSManager, rest_api_handle:BinanceRestapi):
    # create rest api manager
    k = WSKlineDF(manager, rest_api_handle)
    while True:
        # sampling
        k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
        time.sleep(1)

# test to see if buffer loss during the process
def test_buffer_identity(manager:WSManager, rest_api_handle:BinanceRestapi, test_logger:LogHandle):
    k = WSKlineDF(manager, rest_api_handle)
    
    # Initialize the stream by calling get_df once
    k.get_df(Symbol.BTCUSDC, CandleInterval.MIN_1)
    
    endpoint = f"{Symbol.BTCUSDC.lower()}_perpetual@continuousKline_{CandleInterval.MIN_1}"
    
    # Wait a bit for the connection and registration to settle
    time.sleep(2)
    
    # Get buffers
    kline_status = k.status.get(endpoint)
    assert kline_status is not None, "Kline status not found"
    wskline_buff = kline_status.buff
    
    manager_route = manager._routing_table.routes.get(endpoint)
    assert manager_route is not None, "Manager route not found"
    
    queue_buffs = manager_route.get("queue")
    assert queue_buffs is not None and len(queue_buffs) > 0, "Manager queue buffer not found"
    manager_buff = queue_buffs[0]
    
    # Print addresses
    test_logger.write_log(f"WSKlineDF buffer address: {hex(id(wskline_buff))}")
    test_logger.write_log(f"WSManager buffer address: {hex(id(manager_buff))}")
    
    assert wskline_buff is manager_buff, "BUFFERS ARE NOT THE SAME INSTANCE!"
    test_logger.write_log("SUCCESS: Buffers are the same instance!")