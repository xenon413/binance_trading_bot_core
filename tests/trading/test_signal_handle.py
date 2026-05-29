from pathlib import Path
from typing import Callable
import pandas as pd
import pytest
from decimal import Decimal

from core.schema.config_schema import Settings
# from trading.signal_handle import SignalHandle
from trading.signal_handle import SignalHandle

BASE_DIR = Path(__file__).resolve().parent

TEST_PATH = BASE_DIR / "test_data/final_backtest.json"

def read_kline_csv(path):
    csv_converters = {
        "open_price":Decimal,
        "high_price":Decimal,
        "low_price":Decimal,
        "close_price":Decimal,
        "volume":Decimal,
        "quote_asset_volume":Decimal,
        "taker_buy_volume":Decimal,
        "taker_buy_quote_asset_volume":Decimal
    }
    # include type casting
    res = pd.read_csv(path, converters=csv_converters)

    # field check
    fields = {
        "open_time", 
        "open_price", 
        "high_price", 
        "low_price", 
        "close_price", 
        "volume", 
        "close_time", 
        "quote_asset_volume", 
        "trade_num", 
        "taker_buy_volume", 
        "taker_buy_quote_asset_volume", 
        "ignore"
    }
    if set(res.columns) != fields:
        assert False, f"field miss match: {set(res.columns)}"
    
    return res

def test_handle_signal(load_settings:Callable[[str], Settings]):
    settings = load_settings(TEST_PATH)
    handle = SignalHandle(settings.trading_bot_settings.kwargs.signal_settings)
    
    # load data
    paths = settings.trading_bot_settings.kwargs.signal_settings.df_config.get_all_path()
    dfs = {k:read_kline_csv(v) for k,v in paths.items()}

    df = handle.config_signal(dfs)
    df.to_csv("res1.csv")

def test_handle_mismatch_signal(load_settings:Callable[[str], Settings]):
    settings = load_settings(TEST_PATH)
    handle = SignalHandle(settings.trading_bot_settings.kwargs.signal_settings)

    # load data
    # cut all df to 1500 lines to sim real situation (when history timestamp not alined)
    paths = settings.trading_bot_settings.kwargs.signal_settings.df_config.get_all_path()
    dfs = {k:read_kline_csv(v).tail(1500) for k,v in paths.items()}

    df = handle.config_signal(dfs)
    # df.to_csv("res2.csv")


    dfs = {k:read_kline_csv(v) for k,v in paths.items()}
    # dfs["sub"] = dfs["sub"].drop(dfs["sub"].index[-1])
    # dfs["sub"] = dfs["sub"].drop(dfs["sub"].index[-1])
    # dfs["sub"] = dfs["sub"].drop(dfs["sub"].index[-1])
    # dfs["sub"] = dfs["sub"].drop(dfs["sub"].index[-1])
    # dfs["sub"] = dfs["sub"].drop(dfs["sub"].index[-1])
    dfs["main"] = dfs["main"].drop(dfs["main"].index[-1])
    dfs["main"] = dfs["main"].drop(dfs["main"].index[-1])
    dfs["main"] = dfs["main"].drop(dfs["main"].index[-1])
    dfs["main"] = dfs["main"].drop(dfs["main"].index[-1])
    dfs["main"] = dfs["main"].drop(dfs["main"].index[-1])
    
    dfs = {k:v.tail(1500) for k, v in dfs.items()}
    df = handle.config_signal(dfs)
    # df.to_csv("res3.csv")