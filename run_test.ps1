# CHEAT SHEET


# -v / -vv: Increases verbosity. -vv ensures full diffs are shown for failed assertions (no ... truncation).

# -s: Disables output capture. Allows you to see print() statements and logs in real-time.

# -q: Quiet mode. Reduces output to just the dots and the final summary.

# --color=yes: Forces colorized output (useful for CI/CD logs).

# --tb=style: Controls traceback style (long, short, line, native, or no).


# -k "expression": Runs tests that match a keyword string (e.g., pytest -k "login").

# -m "marker": Runs tests decorated with a specific marker (e.g., @pytest.mark.slow).

# -x / --exitfirst: Stops the test session immediately after the first failure.

# --maxfail=n: Stops the test session after n failures.

# path/to/test_file.py: Runs only the tests within a specific file.


# --lf (last-failed): Only reruns the tests that failed during the last run.

# --ff (failed-first): Runs all tests, but starts with the ones that failed last time.

# -rf: Shows a summary of failed tests at the end. (Use -ra for all except passed).

# --durations=n: Shows the n slowest tests (great for optimizing slow suites).

# --pdb: Drops you into the Python Debugger immediately at the point of failure.


# --collect-only: Shows which tests would run without actually running them.

# --fixtures: Lists all available fixtures (including built-in ones like tmpdir or capsys).

# -c file: Loads configuration from a specific file (like pytest.ini or tox.ini).


# $env:PYTHONPATH = "."

# test all
# pytest -vv -rf --color=yes

# required test before start running
# pytest -m precheck -vv -rf --color=yes
# pytest -m "precheck not fixme" -vv -rf --color=yes

# all the ones that haven't been fixed
# pytest -m fixme -vv -rf --color=yes

# test rest api
# pytest binance_trading_bot\tests\core\binance_api\rest_api -v -rf --color=yes

# test ws api
# pytest binance_trading_bot\tests\core\binance_api\ws_api -vv -rf --color=yes

# test log handle
# pytest binance_trading_bot\tests\core\test_log_handle.py -vv -rf --color=yes

# test load schema
# pytest binance_trading_bot\tests\config_schema\test_load_schema.py -vv -rf --color=yes

# test signal config
pytest binance_trading_bot\tests\trading\test_signal_handle.py -svv -rf --color=yes

# test run engine (when in backtest mode)
# pytest binance_trading_bot\tests\trading\test_engine.py -vv -rf --color=yes

# test ws stream
# pytest -m fixme binance_trading_bot\tests\core\binance_api\ws_stream\test_market_stream.py -vv -rf --color=yes --count=600 -x
# pytest -m precheck binance_trading_bot\tests\core\binance_api\ws_stream\test_market_stream.py -vv -rf --color=yes
# pytest binance_trading_bot\tests\core\binance_api\ws_stream\test_market_stream.py::test_kline_df3 -vv -rf --color=yes
# Read-Host -Prompt "Press Enter to exit"