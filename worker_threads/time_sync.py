'''
TODO: need solution for other operating system
'''
import subprocess
import ntplib
import time

from core import Base, LogLevel

CRITICAL = False

class TimeSync(Base):
    def __init__(self, thresh:float, ntp_server:list, cycle:int):
        super().__init__(CRITICAL)
        self._thresh = thresh
        self._ntp_server = ntp_server
        self._cycle = cycle
        
    # ---------- Windows Time Service ----------
    def _start_time_service(self)->None:
        try:
            status = subprocess.run(
                ["sc", "query", "w32time"],
                capture_output=True, text=True
            )
            if "RUNNING" not in status.stdout:
                self._log_handle.write_log("starting windows time service...", LogLevel.DEBUG)
                subprocess.run(["sc", "start", "w32time"], capture_output=True, text=True)

        except Exception as e:
            self._log_handle.write_log(f"could not check/start service: {e}", LogLevel.WARNING)

    # ---------- NTP Drift Check ----------
    def _get_ntp_time_offset(self)->int|None:
        for server in self._ntp_server:
            try:
                c = ntplib.NTPClient()
                response = c.request(server, version=3, timeout=2)
                return response.offset
            
            except Exception as e:
                self._log_handle.write_log(f"failed to get NTP time: {e} server: {server}", LogLevel.WARNING)

        return None

    def _sync_time(self)->bool:
        try:
            result = subprocess.run(["w32tm", "/resync"], capture_output=True, text=True)
            if result.returncode == 0:
                self._log_handle.write_log("time sync success", LogLevel.INFO)
                return True
            else:
                self._log_handle.write_log(f"time sync failed: {result.stderr.strip()}", LogLevel.WARNING)
                return False
        except Exception as e:
            self._log_handle.write_log(f"Error during sync: {e}", LogLevel.WARNING)
            return False

    # could direct call
    def check_and_sync(self):
        self._start_time_service()
        offset = abs(self._get_ntp_time_offset())
        if offset is None:
            self._log_handle.write_log("skipping sync due to NTP failure", LogLevel.WARNING)
        elif offset > self._thresh:
            self._log_handle.write_log(f"offset {offset:.3f}s exceeds threshold {self._thresh}s. syncing...", LogLevel.INFO)
            self._sync_time()
        else:
            self._log_handle.write_log(f"offset {offset:.3f}s within threshold. no sync needed.", LogLevel.DEBUG)

    def _loop(self)->None:
        self.check_and_sync()
        time.sleep(self._cycle)
