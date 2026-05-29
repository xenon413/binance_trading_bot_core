from pathlib import Path
from typing import Callable
import time

from core.schema.config_schema import Settings
from trading.engine import Engine

BASE_DIR = Path(__file__).resolve().parent
TEST_PATH = BASE_DIR / "test_data/demo_backtest.json"
TEST_PATH = BASE_DIR / "test_data/fitting_backtest.json"
TEST_PATH = BASE_DIR / "test_data/final_backtest.json"
# TEST_PATH = BASE_DIR / "test_data/fitting_record.json"

def test_backtest(load_settings:Callable[[str], Settings]):
    settings = load_settings(TEST_PATH)
    engine = Engine(settings.trading_bot_settings.kwargs)
    engine.start()
    while True:
        if engine.exit_code == 0:
            break
        
        elif engine.exit_code is not None:
            assert False, engine.exit_code
            
        time.sleep(1)
