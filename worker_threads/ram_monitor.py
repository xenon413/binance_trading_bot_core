import psutil
import time

from core import Base, LogLevel

CRITICAL = False

class RamMonitor(Base):
    def __init__(self):
        super().__init__(CRITICAL)

    def _loop(self):
        self._log_handle.write_log(f"ram usage: {str(psutil.virtual_memory().percent)}%", LogLevel.DEBUG)
        time.sleep(1)

'''
convert this to system monitor 

gemini example:

import psutil
import os

def monitor_system(self):
    process = psutil.Process(os.get_pid())
    
    # Get RAM usage (in MB)
    ram_mb = process.memory_info().rss / (1024 * 1024)
    
    # Get CPU usage (Process specific)
    # Note: interval=None makes this non-blocking
    cpu_usage = process.cpu_percent(interval=None) 
    
    # Get Thread count
    thread_count = len(process.threads())
    
    # Log or handle warnings
    if cpu_usage > 80:
        self.logger.warning(f"High CPU Usage detected: {cpu_usage}%")
        
    return {
        "cpu": cpu_usage,
        "ram": ram_mb,
        "threads": thread_count
    }


'''