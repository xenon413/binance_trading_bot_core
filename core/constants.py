from enum import IntEnum, StrEnum
import logging
from typing import Literal

# TODO: add this into system
class Cross(StrEnum):
    GOLDEN="GOLDEN"
    DEATH="DEATH"

    @classmethod
    def mtp2type(cls, mtp:Literal[-1, 1]):
        return cls.GOLDEN if mtp == 1 else cls.DEATH
    
class Symbol(StrEnum):
    BTCUSDC="BTCUSDC"
    BTCUSDT="BTCUSDT"
    ETHUSDT="ETHUSDT"

class CandleInterval(StrEnum):
    MIN_1="1m"
    MIN_3="3m"
    MIN_5="5m"
    MIN_15="15m"
    MIN_30="30m"
    HOUR_1="1h"
    HOUR_2="2h"
    HOUR_4="4h"
    HOUR_6="6h"
    HOUR_8="8h"
    HOUR_12="12h"
    DAY_1="1d"
    DAY_3="3d"
    WEEK_1="1w"

    @property
    def seconds(self)->int:
        '''Get the interval in seconds'''
        mapping={
            "1m": 60,"3m": 180,"5m": 300,"15m": 900,"30m": 1800,
            "1h": 3600,"2h": 7200,"4h": 14400,"6h": 21600,"8h": 28800,
            "12h": 43200,"1d": 86400,"3d": 259200,"1w": 604800
        }
        return mapping.get(self, 0)
    
    @property
    def ms(self)->int:
        return self.seconds*1000
    
class OrderBookLimit(IntEnum):
    LVL_5=5
    LVL_10=10
    LVL_20=20
    LVL_50=50
    LVL_100=100
    LVL_500=500
    LVL_1000=1000

class MarginType(StrEnum):
    CROSSED="CROSSED"
    ISOLATED="ISOLATED"

class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"

    def get_type(self):
        limit_types = {OrderType.LIMIT, OrderType.STOP, OrderType.TAKE_PROFIT}
        return "limit" if self in limit_types else "market"
    
class OrderSide(StrEnum):
    BUY="BUY"
    SELL="SELL"

class PositionSide(StrEnum):
    BOTH="BOTH" # Use for One-Way Mode
    LONG="LONG" # Use for Hedge Mode
    SHORT="SHORT" # Use for Hedge Mode

class TimeInForce(StrEnum):
    GTC="GTC" # Good Till Cancel
    IOC="IOC" # Immediate or Cancel
    FOK="FOK" # Fill or Kill
    GTX="GTX" # Post Only
    GTD="GTD" # Good Till Date

class ContractType(StrEnum):
    PERPETUAL="PERPETUAL"
    CURRENT_QUARTER="CURRENT_QUARTER"
    NEXT_QUARTER="NEXT_QUARTER"
    TRADIFI_PERPETUAL="TRADIFI_PERPETUAL"
    
    # New transient states found in 2026
    CURRENT_QUARTER_DELIVERING = "CURRENT_QUARTER DELIVERING"
    NEXT_QUARTER_DELIVERING = "NEXT_QUARTER DELIVERING"

class PriceMatch(StrEnum):
    OPPONENT="OPPONENT"
    OPPONENT_5="OPPONENT_5"
    OPPONENT_10="OPPONENT_10"
    OPPONENT_20="OPPONENT_20"
    QUEUE="QUEUE"
    QUEUE_5="QUEUE_5"
    QUEUE_10="QUEUE_10"
    QUEUE_20="QUEUE_20"
    NONE="NONE" # just for matching request return

class OrderStatus(StrEnum):
    NEW="NEW"
    CANCELED="CANCELED"
    EXPIRED="EXPIRED"
    PARTIALLY_FILLED="PARTIALLY_FILLED"
    FILLED="FILLED"
    REJECTED="REJECTED"

class Bool(StrEnum):
    TRUE="true"
    FALSE="false"

    @classmethod
    def from_bool(cls, value: bool):
        return cls.TRUE if value else cls.FALSE
    
# general 
class BotAction(StrEnum):
    RETRY = "RETRY"
    RETURN = "RETURN"
    EXIT = "EXIT"
    RESTART = "RESTART"
    
class LogLevel(IntEnum):
    # default level
    DEBUG=10
    INFO=20
    WARNING=30
    ERROR=40
    CRITICAL=50

    # additional level
    TRADE=25
    
    @classmethod
    def register_levels(cls):
        for level in cls:
            logging.addLevelName(level.value, level.name)
            # Optional: also attach to the logging module for logging.SUCCESS style access
            setattr(logging, level.name, level.value)

# http
class RequestMethod(StrEnum):
    GET="GET"
    POST="POST"
    PUT="PUT"
    DELETE="DELETE"

class BotMode(StrEnum):
    # on live server
    LIVE_TRADE="LIVE_TRADE"
    # on test server
    TEST_TRADE="TEST_TRADE"
    # no order just record entry/exit
    RECORD="RECORD"
    # use 1s data to simulate real trade
    SIMULATE="SIMULATE"
    # use previous data
    BACKTEST="BACKTEST"
    # to match with every real trade data independently 
    BACKTEST_SINGLE="BACKTEST_SINGLE"
    
LogLevel.register_levels()