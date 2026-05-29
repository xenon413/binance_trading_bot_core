import platform
import subprocess
import time
import speedtest
import requests
import json

from core import Base, LogLevel, BinanceError

# defult setting
REST1 = 1
REST2 = 600
REST3 = 1
CRITICAL = False

class WifiMonitor1(Base):
    def __init__(self, rest:int=None):
        super().__init__(CRITICAL)
        self.rest = rest or REST1
            
    def _loop(self):
        param = "-n" if platform.system().lower() == "windows" else "-c"
        command = ["ping", param, "1", "8.8.8.8"]

        try:
            result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            if result.returncode != 0:
                self._log_handle.write_log("wifi disconnect", LogLevel.WARNING)
                return False
            else:
                self._log_handle.write_log("wifi connect", LogLevel.DEBUG)
                return True

        except Exception:
            self._log_handle.write_log("wifi disconnect", LogLevel.WARNING)
            return False
        
        finally:
            time.sleep(self.rest)

class WifiMonitor2(Base):
    def __init__(self, rest:int=None):
        super().__init__(CRITICAL)
        self.rest = rest or REST2

    def _loop(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()

            download_speed = st.download() / 1_000_000
            upload_speed = st.upload() / 1_000_000
            ping = st.results.ping

            self._log_handle.write_log(f"ping: {ping:.2f} ms, download: {download_speed:.2f} Mbps, upload: {upload_speed:.2f} Mbps", LogLevel.INFO)
            return True
        except Exception as e:
            self._log_handle.write_log(f"no internet connection or test failed: {e}", LogLevel.WARNING)
            return False

        finally:
            time.sleep(self.rest)

class WifiMonitor3(Base):
    def __init__(self, rest:int=None):
        super().__init__(CRITICAL)
        self.rest = rest or REST3
        self.sesssion = requests.Session()

    def _loop(self):
        try:
            start = time.time()
            r = self.sesssion.get("https://fapi.binance.com/fapi/v1/ping", timeout=5)
            end = time.time()
            res = json.loads(r.text)
            self._log_handle.write_log(f"{r.headers}", LogLevel.DEBUG)
            if 400 <= r.status_code <= 599:
                error_code = res["code"]
                self._log_handle.write_log(f"in wifi_monitor request error: {res}", LogLevel.WARNING)
                if error_code == BinanceError.TOO_MANY_REQUESTS:
                    time.sleep(120)
                    self._log_handle.write_log(f"too many requests pause 120s", LogLevel.WARNING)

            self._log_handle.write_log(f"ping speed: {end - start}", LogLevel.DEBUG)
            return True
        except Exception as e:
            self._log_handle.write_log(f"in wifi_monitor request error: {e}", LogLevel.WARNING)
            return False

        finally:
            time.sleep(self.rest)