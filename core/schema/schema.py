from __future__ import annotations
from ..my_base_model import MyBaseModel
from decimal import Decimal
from ..constants import PositionSide, OrderSide
import time
import json

from typing import Callable, Optional, Any

from pydantic import ConfigDict

# general recording, use in strat to record more data that's not order related
class Event(MyBaseModel):
    time:int
    info:dict[str, Any]={}
    is_final:Optional[bool]=None # mark as final of the order

    # use for when needed to record export json string
    def to_jsons(self, event_type:str="event")->str:
        log_entry = {
            "event_time": int(time.time()*1000),
            "type":event_type,
            "payload":self.model_dump(exclude_none=True)
        }
        return json.dumps(log_entry, default=str)

class OpenOrder(Event):
    margin_pct:Decimal
    price:Decimal
    position_side:PositionSide
    leverage:int

    def to_jsons(self, event_type:str="open")->str:
        return super().to_jsons(event_type)
    
    @property
    def order_side(self)->OrderSide:
        if self.position_side == PositionSide.LONG:
            return OrderSide.BUY
        
        return OrderSide.SELL
    
class CloseOrder(Event):
    position_pct:Decimal
    price:Decimal
    position_side:PositionSide
    
    def to_jsons(self, event_type:str="close")->str:
        return super().to_jsons(event_type)
    
    @property
    def order_side(self)->OrderSide:
        if self.position_side == PositionSide.LONG:
            return OrderSide.SELL
        
        return OrderSide.BUY
    
class ExecuteOrder(Event):
    open_price:Decimal
    open_qty:Decimal
    filled_canceled_time:int
    filled_price:Decimal
    filled_qty:Decimal
    
    def to_jsons(self, event_type:str="execute")->str:
        return super().to_jsons(event_type)
    
class SignalStatus(MyBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    next_target:Callable[[Any], SignalStatus]
    next_kwargs:dict={}
    wait:int=0 # wait n klines
    event:Optional[Event]=None # event handled in action

    def next(self, **kwargs:Any)->SignalStatus:
        '''return next signalStatus '''
        next_state:SignalStatus = self.next_target(**self.next_kwargs, **kwargs)
        return next_state

    # def __eq__(self, other:object)->bool:
    #     if not isinstance(other, SignalStatus):
    #         return False
        
    #     return (
    #         self.wait == other.wait and
    #         self.next_kwargs == other.next_kwargs and
    #         self.event == other.event and 
    #         self.next_target == other.next_target
    #     )
