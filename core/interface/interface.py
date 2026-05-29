from typing import Protocol, runtime_checkable
import pandas as pd

# ---- create interface for strat ----
@runtime_checkable
class StratInterface(Protocol):
    def __init__(self)->None:...

    def reset(self)->None:...

    def update(self, row:pd.Series, **kwargs):...

    def _signal_open(self):...

StratType = type[StratInterface]

# ---- create interface for base thread class ----
@runtime_checkable
class BaseInterface(Protocol):
    
    def __init__(self)->None:...

    def start(self)->None:...

    def stop(self)->None:...

    def _loop(self)->None:...

BaseType = type[BaseInterface]
