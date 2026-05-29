from __future__ import annotations
from typing import Callable, Any, Optional, TYPE_CHECKING
from pydantic import model_validator

from ..my_base_model import MyBaseModel
from .bot_schema import TradingBotKwargs
from .worker_schema import TimeSyncConfig, WifiMonitorConfig, RamMonitorConfig
from ..interface.interface import BaseType
from ..exceptions import BotAction, BotError
if TYPE_CHECKING:
    from ..interface.interface import BaseInterface

# ---- settings ----
class TradingBot(MyBaseModel):
    target:BaseType
    kwargs:TradingBotKwargs

    def start(self)->dict[str, BaseInterface]:
        inst = self.target(self.kwargs)
        inst.start()
        return {"trading_bot":inst}

class Worker(MyBaseModel):
    time_sync_handle:Optional[TimeSyncConfig]
    wifi_monitor1_handle:Optional[WifiMonitorConfig]
    wifi_monitor2_handle:Optional[WifiMonitorConfig]
    wifi_monitor3_handle:Optional[WifiMonitorConfig]
    ram_monitor:Optional[RamMonitorConfig]

    def start_all(self)->dict[str, BaseInterface]:
        inst = {}
        for field in self.__class__.model_fields:
            if field is None: continue
            handler:TimeSyncConfig|WifiMonitorConfig|RamMonitorConfig = getattr(self, field)
            temp = handler.start()
            inst |= {field:temp}

        return inst

class Settings(MyBaseModel):
    trading_bot_settings:TradingBot
    worker_settings:Worker

    def start_all(self)->list[BaseInterface]:
        inst = self.worker_settings.start_all()
        inst |= self.trading_bot_settings.start()
        return inst

    @model_validator(mode='after')
    def validate_all(self):
        bot = self.trading_bot_settings.kwargs

        # check engine settings
        bot._check_df_path()
        bot.engine_settings._check_req()

        # check all index in signal_settings
        bot.signal_settings.df_config.main.index._check_config_one()
        if bot.signal_settings.df_config.others:
            for i in bot.signal_settings.df_config.others.values():
                i.index._check_config_one()
        return self
    

