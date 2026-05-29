from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DEMO_PATH = BASE_DIR / "test_data/demo_backtest.json"
def test_load_demo_schema(load_settings):
    load_settings(BASE_DIR / "test_data/demo_backtest.json")
    load_settings(BASE_DIR / "test_data/demo_record.json")
    load_settings(BASE_DIR / "test_data/demo_test_trade.json")

FITTING_PATH = BASE_DIR / "test_data/fitting_backtest.json"
def test_load_fitting_schema(load_settings):
    load_settings(FITTING_PATH)


