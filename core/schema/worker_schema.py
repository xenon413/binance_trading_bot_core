from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from ..interface.interface import BaseType, BaseInterface
from ..my_base_model import MyBaseModel

# ---- define timesync handle ----
class TimeSyncKwargs(MyBaseModel):
    thresh:Optional[float] = 0.5
    ntp_server:Optional[list[str]] = ["pool.ntp.org", "time.google.com", "time2.google.com"]
    cycle:Optional[float] = 3600

    @field_validator('thresh', 'ntp_server', 'cycle', mode='before')
    @classmethod
    def prevent_none(cls, v, info):
        # If the input is explicitly None, return the field's default value
        if v is None:
            return cls.model_fields[info.field_name].default
        return v
    
class TimeSyncConfig(MyBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    target:BaseType
    kwargs:TimeSyncKwargs

    def start(self)->BaseInterface:
        inst = self.target(**self.kwargs.model_dump())
        inst.start()
        return inst
    
# ---- define memory monitor ----
class RamMonitorConfig(MyBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    target:BaseType
    kwargs:dict

    def start(self)->BaseInterface:
        inst = self.target(**self.kwargs)
        inst.start()
        return inst
    
# ---- define wifi monitors ----
class WifiMonitorKwargs(MyBaseModel):
    rest:Optional[float] = None

class WifiMonitorConfig(MyBaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    target:BaseType
    kwargs:WifiMonitorKwargs

    def start(self)->BaseInterface:
        inst = self.target(**self.kwargs.model_dump())
        inst.start()
        return inst