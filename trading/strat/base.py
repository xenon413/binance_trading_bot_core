from abc import ABC, abstractmethod
import pandas as pd
from core.schema.bot_schema import StratKwargs
from core.schema.schema import SignalStatus, OpenOrder, CloseOrder, Event
from core.constants import PositionSide

class Strat(ABC):
    def __init__(self, strat_kwargs:StratKwargs):
        self.strat_config = strat_kwargs.strat_config
        self._stat: SignalStatus = None
        self.reset()

    def reset(self):
        self._stat = SignalStatus(
            next_target=self._signal_open,
            next_kwargs={},
            event=None,
            wait=0
        )

    @property
    def stat(self):
        return self._stat
    
    @stat.setter
    def stat(self, val:SignalStatus):
        # not sure if direct assign is a good idea
        # maybe assign by value will be better?
        self._stat = val

    def update(self, row:dict, **kwargs)->SignalStatus:
        self._stat = self._stat.next(row=row, **kwargs)
        return self._stat

    @abstractmethod
    def _signal_open(self, row, **kwargs):
        '''starting point of the strat'''

__all__ = [
    "Strat",
    "StratKwargs",
    "SignalStatus",
    "OpenOrder",
    "CloseOrder",
    "Event",
    "PositionSide"
]