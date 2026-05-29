import time
from functools import wraps
import sys
import random
import copy
import inspect
from typing import Callable, TypeVar, Any

from .constants import *
from .exceptions import *
from .log_handle import LogHandle

# Define TypeVar bound to any Callable to preserve method signatures for static type checkers (IDEs)
F = TypeVar('F', bound=Callable[..., Any])

# error handle
def error_handle(func: F) -> F:
    # check if self/cls exist in the function params
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        has_self = len(params) > 0 and params[0] in ('self', 'cls')
    except Exception:
        has_self = False

    def get_safe_args(args: tuple, kwargs: dict):
        safe_args_list = []
        # TODO: confirm if skipping copy is a good idea
        # skip copy for self/cls  
        if has_self and len(args) > 0:
            safe_args_list.append(args[0])
            start_idx = 1
        else:
            start_idx = 0
    
        # try copy args
        for arg in args[start_idx:]:
            try:
                safe_args_list.append(copy.deepcopy(arg))
            except Exception:
                try:
                    safe_args_list.append(copy.copy(arg))
                except Exception:
                    safe_args_list.append(arg)

        # try copy kwargs
        safe_kwargs = {}
        for k, v in kwargs.items():
            try:
                safe_kwargs[k] = copy.deepcopy(v)
            except Exception:
                try:
                    safe_kwargs[k] = copy.copy(v)
                except Exception:
                    safe_kwargs[k] = v

        return tuple(safe_args_list), safe_kwargs

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        error_counts = {}
        # to prevent accidental mutation on something... i forgot what it was 
        safe_args, safe_kwargs = get_safe_args(args, kwargs)
        while True:
            try:
                return func(*safe_args, **safe_kwargs)
            except BotError as e:
                if e.action is BotAction.EXIT:
                    sys.exit(e)

                elif e.action is BotAction.RESTART:
                    sys.exit(e)

                elif e.action is BotAction.RETURN:
                    return e

                elif e.action is BotAction.RETRY:
                    current_n = error_counts.get(e.message, 0) + 1
                    error_counts[e.message] = current_n
                    if current_n > e.max_retry:
                        sys.exit(f"max retry reached: {e}")

                    backoff = e.init_wait + e.base_wait**current_n + random.randint(0, 999) * 0.001
                    time.sleep(backoff)
                    
    return wrapper

# useful for debug if ever needed
def log_lifecycle(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        lh = LogHandle(name="log_lifecycle")
        start_time = time.perf_counter()
        lh.write_log(f"ENTER {func.__name__} | Args: {args}", LogLevel.DEBUG)
        try:
            return func(*args, **kwargs)   
        except Exception as e:
            lh.write_log(f"EXCEPTION in {func.__name__}: {str(e)}", LogLevel.INFO)
            raise
        finally:
            end_time = time.perf_counter()

            lh.write_log(f"exit {func.__name__} (duration: {end_time-start_time})", LogLevel.DEBUG)
    return wrapper

# due to api limits and the difference on computing speed, implement a dynamic wait for functions
def set_min_process_time(seconds:float)->F:
    '''
    args
        seconds: the total second for the process
    '''
    def decorator(func:F)->F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            lh = LogHandle(name="set_min_proccess_time")
            start_time = time.perf_counter()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                lh.write_log(f"EXCEPTION in {func.__name__}: {str(e)}", LogLevel.INFO)
                raise
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                delay = max(seconds - duration, 0)
                if delay != 0:
                    lh.write_log(f"delay {delay}s to meet {seconds}s process time", LogLevel.DEBUG)
                time.sleep(delay)

        return wrapper
    return decorator

def redirect(target:Callable|str):
    '''
        if called by instant's function pass in str
        if called by static function pass in class
    '''
    def decorator(func):
        try:
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            has_self = len(params) > 0 and params[0] == 'self'
        except Exception:
            has_self = False

        # TODO: could simplify/flatten to single condition
        if has_self:
            # Rule: Instance methods MUST redirect via a string name within the same class
            if not isinstance(target, str):
                raise TypeError(
                    f"Scope Error: '{func.__name__}' is an instance method (has 'self'). "
                    f"It can only redirect to another method in the same class using a string name, "
                    f"not a direct callable object like '{target}'."
                )
        else:
            # Rule: Static/Standalone functions CANNOT redirect using a string lookup
            if isinstance(target, str):
                raise TypeError(
                    f"Scope Error: '{func.__name__}' is a static or standalone function. "
                    f"It cannot redirect to a string target '{target}'. Pass the actual function object instead."
                )
            
        @wraps(target)
        def wrapper(*args, **kwargs):
            if has_self:
                # Execution for Instance Methods
                if not args:
                    raise TypeError(f"Method '{func.__name__}' called without an instance.")
                self_instance = args[0]
                
                # Double-check that the target actually exists on this specific class instance
                if not hasattr(self_instance, target):
                    raise AttributeError(
                        f"'{type(self_instance).__name__}' object has no method '{target}' to redirect to."
                    )
                
                target_callable = getattr(self_instance, target)
                return target_callable(*args[1:], **kwargs)
            else:
                return target(*args, **kwargs)
            
        return wrapper
    return decorator
