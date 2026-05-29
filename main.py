import subprocess
import ctypes
import sys 
import traceback
import os
import inspect
import time
import argparse
import json

from core import error_handle, LogHandle, LogLevel, BotMode
from core.schema.config_schema import Settings
from core.interface.interface import BaseInterface
from utils import Alarm
from trading.engine import Engine
from trading import strat
import worker_threads

### for dev convenience 
DEFAULT_CONFIG_PATH = r"binance_trading_bot\config\final_record.json"
# DEFAULT_CONFIG_PATH = r"binance_trading_bot\config\fitting.json"

def hydrate(map, data, target_key="target"):
    if isinstance(data, dict):
        return {k: (map[v] if k == target_key and v in map else hydrate(map, v, target_key)) 
                for k, v in data.items()}
    return data

class Bot:
    def __init__(self)->None:
        self.services:dict[str, BaseInterface] = {}
        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)

        args = self._parse_arguments()
        config_path = args.config

        self.config_data:Settings = self.load_config(config_path)

    def _parse_arguments(self):
        """Internal helper to handle command line arguments."""
        parser = argparse.ArgumentParser(
            description="Trading Bot Script",
            usage="python main.py -c <path_to_config>",
            add_help=True
        )
        parser.add_argument(
            "-c", "-C", "--config",
            type=str,
            default=DEFAULT_CONFIG_PATH,
            help="Path to the configuration file"
        )
        ### add way to load in batch in a folder
        ### if backtest run in queue if live/test server run in parallel
        ### could mix different mode

        return parser.parse_args()
  
    def load_config(self, config_path: str) -> Settings:
        """Handles reading, hydrating, and validating the configuration file."""
        # 1. Read file
        if not os.path.exists(config_path):
            sys.exit(f"The file {config_path} does not exist")

        with open(config_path, "r") as f:
            raw_data = json.load(f)
            self._log_handle.write_log(f"Successfully loaded config: {config_path}", LogLevel.INFO)

        # 2. Build class map for hydration
        # Combines Engine, Strategies, and Workers into one lookup dictionary
        class_map = {Engine.__name__: Engine}
        strat_map = {name: obj for name, obj in inspect.getmembers(strat, inspect.isclass)}
        worker_map = {name: obj for name, obj in inspect.getmembers(worker_threads, inspect.isclass)}
        
        class_map.update(strat_map)
        class_map.update(worker_map)

        # 3. Log availability
        self._log_handle.write_log(f"Available strats: {list(strat_map.keys())}", LogLevel.INFO)
        self._log_handle.write_log(f"Available workers: {list(worker_map.keys())}", LogLevel.INFO)

        # 4. Hydrate (Replace "target" strings with actual Class objects)
        hydrated_data = hydrate(class_map, raw_data)

        # 5. Validate and return as Settings object
        return Settings(**hydrated_data)

    @error_handle
    def starter(self)->None:
        self.services = self.config_data.start_all()

        self._log_handle.write_log(f"service start: {len(self.services)}", LogLevel.INFO)
        
        # error handle
        while True:
            self.error_handle()
            time.sleep(1)

    def error_handle(self)->None:
        for key, val in self.services.items():
            if (not val.is_running) and (not val.exit):
                # if critical
                if val.critical:
                    sys.exit(f"critical thread {key} stopped unexpectly")
                
                self._log_handle.write_log(f"thread {key} stopped unexpectly", LogLevel.CRITICAL)

    # not functioning
    # TODO: fix
    def stop_all(self)->None:
        for key, val in self.services.items():
            val.stop()
            self._log_handle.write_log(f"stop thread: {key}", LogLevel.INFO)

def set_admin():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # Relaunch as admin using PowerShell (directly runs python.exe)
        subprocess.run([
            "powershell",
            "-NoProfile",
            "-Command",
            "Start-Process",
            f'"{sys.executable}"',
            "-ArgumentList",
            " ".join(f'"{a}"' for a in sys.argv),
            "-Verb",
            "RunAs"
        ])
        sys.exit(0)

if __name__ == "__main__":
    set_admin()
    lh = LogHandle()
    lh.write_log("ver 1.4.0", LogLevel.INFO)
    bot1 = None

    try:
        bot1 = Bot()
        bot1.starter()
    except (Exception, SystemExit) as e:
        # Check if it's a "clean" SystemExit (code 0 or None)
        if isinstance(e, SystemExit) and (e.code == 0 or e.code is None):
            # Just re-raise to let the finally block handle it without logging
            pass 
        else:
            # log error message for crashes, non-zero exits, and all other Exceptions
            t = traceback.format_exc()
            lh.write_log(e, LogLevel.CRITICAL)
            lh.write_log(t, LogLevel.CRITICAL)

    finally:
        if not bot1:
            input("Bot failed to initialize. Press Enter to exit...")

        elif bot1.config_data.trading_bot_settings.kwargs.engine_settings.mode in (BotMode.BACKTEST, BotMode.BACKTEST_SINGLE, BotMode.SIMULATE):
            input("Bot finished. Press Enter to exit...")

        else:
            # alarm
            path = os.path.abspath(inspect.getfile(Alarm))
            subprocess.Popen([sys.executable, path], creationflags=subprocess.CREATE_NEW_CONSOLE)

            # clear all thread
            bot1.stop_all()
            input("Bot Error. Press Enter to exit...")

