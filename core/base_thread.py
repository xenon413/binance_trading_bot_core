from abc import ABC, abstractmethod
import threading
import asyncio
import traceback

from .log_handle import LogHandle
from .constants import LogLevel, BotAction
from .decorators import error_handle
from .exceptions import BotError, BinanceError


class BaseAPI(ABC):
    def __init__(self):
        self._log_handle = LogHandle(name=self.__class__.__name__)
        self._process = None
        self._exit = False

    @abstractmethod
    async def start(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def _loop(self):
        pass

class BaseThread(BaseAPI):
    def __init__(self):
        super().__init__()
        self._loop_ref = None
        self._task_ref = None

    @property
    def is_running(self):
        return self._process and self._process.is_alive()
    
    async def start(self):
        if self.is_running:
            return

        def wrapper():
            # A thread MUST create its own event loop to run 'async' code
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop_ref = loop
            @error_handle
            async def worker():
                try:
                    while self.is_running and not self._exit:
                        await self._loop()
                except asyncio.CancelledError:
                    self._log_handle.write_log("worker canceled", LogLevel.WARNING)

                except Exception as e:
                    raise BotError(f"unexpected error: {e}", BotAction.EXIT)
                
            self._task_ref = loop.create_task(worker())
            try:
                loop.run_until_complete(self._task_ref)
            finally:
                loop.close()
                
        self._process = threading.Thread(target=wrapper, daemon=True)
        self._process.start()

    @error_handle
    async def stop(self):
        self._exit = True
        if self._loop_ref and self._task_ref:
            self._loop_ref.call_soon_threadsafe(self._task_ref.cancel)

        if self.is_running:
            self._process.join(timeout=5)
            if self._process.is_alive():
                # total wait: 10+10+2^5+2^4+2^3+2^2+2=82
                raise BotError("thread stuck", BotAction.RETRY, 10, 2, 5)
            
        self._process = None
        self._exit = False

class BaseAsync(BaseAPI):
    def __init__(self):
        super().__init__()

    @property
    def is_running(self):
        return self._process and not self._process.done()
    
    async def start(self):
        if self.is_running:
            return
        
        @error_handle
        async def worker():
            try:
                while self.is_running:
                    await self._loop()

            except asyncio.CancelledError:
                # Handle cleanup if the task is cancelled via stop()
                pass

        self._process = asyncio.create_task(worker())

    async def stop(self):
        self._exit = True
        if self.is_running:
            self._process.cancel()
            try:
                # Wait for the worker to finish its finally block
                await asyncio.wait_for(self._process, timeout=5.0)
                if not self._process.done():
                    raise BinanceError("async stuck", BotAction.RETRY, 10, 2, 5)
            except asyncio.CancelledError:
                pass
        self._process = None
        self._exit=False

class Base:
    '''
    the original version of base class without async
    '''
    def __init__(self, critical=True):
        self._log_handle = LogHandle(self.__class__.__name__, self.__class__.__name__)
        self._process = None
        self.exit = False
        self.critical = critical
        self.exit_code = None

    @property
    def is_running(self)->bool:
        return self._process and self._process.is_alive()
    
    def start(self):
        self.exit_code = None
        if self.is_running:
            return
        
        @error_handle
        def worker():
            try:
                while self.is_running and not self.exit:
                    self._loop()
                
                self.exit_code = 0
                self._process = None
                self.exit = False
                
            except (Exception, SystemExit) as e:
                t = traceback.format_exc()
                self._log_handle.write_log(e, LogLevel.CRITICAL)
                self._log_handle.write_log(t, LogLevel.CRITICAL)
                self.exit_code = 1

        self._process = threading.Thread(target=worker, daemon=True)
        self._process.start()

    @error_handle
    def stop(self):
        self.exit = True # mark tried to exit
        if self.is_running:
            self._process.join(timeout=5)
            if self.is_running:
                # total wait: 10+10+2^5+2^4+2^3+2^2+2=82
                raise BotError("thread stuck", BotAction.RETRY, 10, 2, 5)
        self._process = None

        # reset to False for start
        self.exit = False

    @abstractmethod
    def _loop(self):
        pass

def create_service(logic_class, threaded=True, *args, **kwargs):
    '''
    the dynamic parents for aysnc/thread parent
    '''
    # Determine the execution strategy
    execution_base = BaseThread if threaded else BaseAsync
    
    # Create the dynamic class
    # Order matters: execution_base comes FIRST so its start/stop are used
    dynamic_name = f"{'Threaded' if threaded else 'Async'}{logic_class.__name__}"
    dynamic_class = type(dynamic_name, (logic_class, execution_base), {})
    
    # Instantiate with any specific args (like symbol="BTCUSDT")
    return dynamic_class(*args, **kwargs)

