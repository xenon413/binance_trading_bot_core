import pytest
import os
import dotenv
import sys
import inspect
import json
from typing import Callable
import logging
from core.log_handle import LogHandle
from core.binance_api.ws_stream.market_stream import WSManager
from core.schema.config_schema import Settings
from core.binance_api.rest_api.rest_api import BinanceRestapi
from trading.engine import Engine
from trading import strat
import worker_threads

# the server to use
TEST = False

@pytest.fixture(scope="session")
def api_credentials():
    __tracebackhide__ = True
    # only use test server
    if TEST:
        key = os.getenv("TEST_KEY")
        secret = os.getenv("TEST_SECRET")
    else:
        key = os.getenv("KEY")
        secret = os.getenv("SECRET")
    
    if not key or not secret:
        pytest.fail("API Credentials missing! Check your .env file.")
        
    return {"key": key, "secret": secret}

@pytest.fixture
def load_settings()->Callable[[str], Settings]:
    def _hydrate(map, data, target_key="target"):
        if isinstance(data, dict):
            return {k: (map[v] if k == target_key and v in map else _hydrate(map, v, target_key)) 
                    for k, v in data.items()}
        return data

    def _load_settings(config_path:str)->Settings:
        """Handles reading, hydrating, and validating the configuration file."""
        # 1. Read file
        if not os.path.exists(config_path):
            sys.exit(f"The file {config_path} does not exist")

        with open(config_path, "r") as f:
            raw_data = json.load(f)

        # 2. Build class map for hydration
        # Combines Engine, Strategies, and Workers into one lookup dictionary
        class_map = {Engine.__name__: Engine}
        strat_map = {name: obj for name, obj in inspect.getmembers(strat, inspect.isclass)}
        worker_map = {name: obj for name, obj in inspect.getmembers(worker_threads, inspect.isclass)}
        
        class_map.update(strat_map)
        class_map.update(worker_map)
        # print(class_map)
        # 4. Hydrate (Replace "target" strings with actual Class objects)
        hydrated_data = _hydrate(class_map, raw_data)

        # 5. Validate and return as Settings object
        return Settings(**hydrated_data)

    return _load_settings

def fail_on_logging_error(handler, record):
        # This will be called if emit() fails (e.g., EncodingError)
        raise RuntimeError(f"Logging failed for record: {record.msg}")

@pytest.fixture
def test_logger():
    logging.Handler.handleError = fail_on_logging_error
    log_handle = LogHandle("test_logger", "test_logger")
    yield log_handle

@pytest.fixture
def rest_api_handle():
    api = BinanceRestapi(TEST)
    yield api
    api.close()

@pytest.fixture()
def manager():
    m = WSManager(TEST)
    yield m
    m.close()

def pytest_configure(config):
    # load env file
    dotenv.load_dotenv()

    # check env file
    check = os.getenv("KEY")
    check = check and os.getenv("SECRET")
    check = check and os.getenv("TEST_KEY")
    check = check and os.getenv("TEST_SECRET")
 
    config.addinivalue_line(
            "markers", "precheck: critical tests required for startup"
        )
    
    config.addinivalue_line(
            "markers", "fixme: critical tests required for startup"
        )