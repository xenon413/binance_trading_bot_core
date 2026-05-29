import os
import threading
import csv
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

# defult setting
LOG_DIR = "logs"

class LogHandle:
    _global_setup_done = False
    lock = threading.Lock()
    log_dir = os.path.abspath(LOG_DIR)
    formater = logging.Formatter(
        "%(created)f | %(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )

    def __init__(self, log_dir="logger", name:str="logger", level:int=logging.DEBUG): 
        LogHandle.setup_global_logging()
        # get abs log dir
        if not log_dir:
            self._log_dir = LogHandle.log_dir
        else:
            self._log_dir = f"{LogHandle.log_dir}/{log_dir}"
        
        # create log folder
        os.makedirs(self._log_dir, exist_ok=True)
        
        # create logger
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # create handler
        if not self._logger.handlers:
            file_handler = TimedRotatingFileHandler(
                f"{self._log_dir}/{name}.log",
                when="midnight",
                interval=1,
                backupCount=10,
                encoding="utf-8",
            )
            file_handler.setFormatter(LogHandle.formater)
            self._logger.addHandler(file_handler)

    @classmethod
    def setup_global_logging(cls):
        with cls.lock:
            if cls._global_setup_done:
                return
            
            os.makedirs(cls.log_dir, exist_ok=True)
            
            # root logger
            root = logging.getLogger()
            root.setLevel(logging.DEBUG)

            # add handles
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(cls.formater)
            root.addHandler(console_handler)
            
            os.makedirs(f"{cls.log_dir}/all", exist_ok=True)
            all_log_handler = TimedRotatingFileHandler(
                f"{cls.log_dir}/all/all.log",
                when="midnight",
                interval=1,
                backupCount=10,
                encoding="utf-8",
            )

            all_log_handler.setLevel(logging.DEBUG)
            all_log_handler.setFormatter(cls.formater)
            root.addHandler(all_log_handler)

            cls._global_setup_done = True
            
    def write_log(self, message:str, level:int=logging.INFO)->None:
        self._logger.log(level, message)
        
if __name__ == "__main__":
    l = LogHandle("test_log")
    l.write_log("test")
