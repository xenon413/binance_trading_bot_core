from core.binance_api.manager import APIManager
from core.schema.config_schema import Settings
from core.constants import (
    Symbol, ContractType, CandleInterval, PriceMatch, OrderSide, PositionSide,
    TimeInForce, OrderType, OrderStatus, MarginType
)
import pytest
from decimal import Decimal

CONFIG_PATH = f""

@pytest.fixture
def api_manager(load_settings):
    settings:Settings = load_settings(CONFIG_PATH)
    yield APIManager(True, settings.trading_bot_settings.kwargs.signal_settings)

@pytest.fixture
def api_manager_no_stream(load_settings):
    settings:Settings = load_settings(CONFIG_PATH)
    manager = APIManager(True, settings.trading_bot_settings.kwargs.signal_settings)
    ### add filter
    yield manager

@pytest.fixture
def api_rest_only_manager(load_settings):
    settings:Settings = load_settings(CONFIG_PATH)
    manager = APIManager(True, settings.trading_bot_settings.kwargs.signal_settings)
    ### add filter
    yield manager

def test_all_normal_calls(api_manager:APIManager):
    api_manager.get_cont_kline_df(Symbol.BTCUSDC, CandleInterval.MIN_1)

    api_manager.get_best_book_price(Symbol.BTCUSDC)

    api_manager.get_server_time()

    api_manager.get_exchange_info()

    api_manager.get_account_balance()

    api_manager.get_account_config()

    api_manager.get_symbol_config(Symbol.BTCUSDC)

def test_change_margin_settings(api_manager:APIManager):
    ### currently assume that initial margin type is isolated
    api_manager.change_margin_type(Symbol.BTCUSDC, MarginType.CROSSED)

    api_manager.change_multi_assets_mode(True)

    api_manager.change_multi_assets_mode(False)

    api_manager.change_margin_type(Symbol.BTCUSDC, MarginType.ISOLATED)

def test_change_position_mode(api_manager:APIManager):
    api_manager.change_position_mode(False)

    api_manager.change_position_mode(True)

def test_change_leverage(api_manager:APIManager):
    api_manager.change_leverage(Symbol.BTCUSDC, 10)

    api_manager.change_leverage(Symbol.BTCUSDC, 1)

def test_order_lifecycle1(api_manager:APIManager):
    '''
    lifesycle: limit order ->modify*2 ->  query -> cancel -> query
    '''
    
    # order
    res = api_manager.new_order(
        symbol=Symbol.BTCUSDC,
        priceMatch=PriceMatch.QUEUE,
        quantity=0.005,
        side=OrderSide.BUY,
        positionSide=PositionSide.LONG,
        timeInForce=TimeInForce.GTX,
        type=OrderType.LIMIT
    )

    # validate 
    assert res.orig_qty == Decimal("0.005"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 1
    res = api_manager.modify_order(
        orderId=res.order_id,
        symbol=Symbol.BTCUSDC,
        side=OrderSide.BUY,
        price=res.price,
        quantity=Decimal("0.006")
    )

    # validate
    assert res.orig_qty == Decimal("0.006"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # modify 2
    res = api_manager.modify_order(
        orderId=res.order_id,
        symbol=Symbol.BTCUSDC,
        side=OrderSide.BUY,
        priceMatch=PriceMatch.QUEUE_20,
        quantity=Decimal("0.007")
    )

    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"
    
    # query
    res = api_manager.query_order(
        symbol=Symbol.BTCUSDC,
        orderId=res.order_id
    )

    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.NEW, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # cancel
    res = api_manager.cancel_order(
        symbol=Symbol.BTCUSDC,
        orderId=res.order_id
    )

    assert res.order_qty == Decimal("0.007"), f"order quantity miss match: {res.order_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"

    # query
    res = api_manager.query_order(
        symbol=Symbol.BTCUSDC,
        orderId=res.order_id
    )

    assert res.orig_qty == Decimal("0.007"), f"order quantity miss match: {res.orig_qty}"
    assert res.status == OrderStatus.CANCELED, f"order status miss match: {res.status}"
    assert res.symbol == Symbol.BTCUSDC, f"order symbol miss match: {res.symbol}"
    assert res.side == OrderSide.BUY, f"order side miss match: {res.side}"
    assert res.time_in_force == TimeInForce.GTX, f"time in force miss match: {res.time_in_force}"
    assert res.orig_type == OrderType.LIMIT, f"order type miss match: {res.orig_type}"
    
### no time to test more come back later
# def test_order_lifecycle2(api_manager:APIManager)

#### come back later after finish engine
#### very important test
def test_drag_order(api_manager:APIManager):
    # no drag order
    pass

def test_drag_order_auto_cancel(api_manager:APIManager):
    pass


### to be continue 
# def test_close_all_position_order()