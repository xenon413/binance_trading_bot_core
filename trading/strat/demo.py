from .base import *
from decimal import Decimal

class DemoStrat(Strat):
    # init pass in as dict because more simple to alter for initialize with min alter
    def __init__(self, strat_kwargs:StratKwargs)->None:
        super().__init__(strat_kwargs)
    
        # ensure included needed data
        self.tp_pct = self.strat_config.others["tp_pct"]
        self.sl_pct = self.strat_config.others["sl_pct"]

    def _signal_open(self, row:dict)->dict:
        entry_price = row["sma_long_short_cross_price"]

        # mtp == cross
        # 1 if gold
        # -1 if death
        # 0 if no cross
        mtp = row["sma_long_short_cross_type"]
        if mtp == 0:
            return SignalStatus(
                next_target=self._signal_open,
                next_kwargs={},
                event=None,
            ) # no wait doesn't effect result
        
        position_side = PositionSide.LONG if mtp > 0 else PositionSide.SHORT
        return SignalStatus(
            next_target=self._signal_close,
            next_kwargs={
                "tp_price":entry_price*(1+self.tp_pct*mtp),
                "sl_price":entry_price*(1-self.sl_pct*mtp),
                "position_side":position_side
            },
            wait=1,
            event=OpenOrder(
                margin_pct=1,
                position_side=position_side,
                price=entry_price,
                time=row["open_time"],
                leverage=self.strat_config.leverage.base,
                info={"cross":"golden" if mtp > 0 else "death"}
            )
        ) # wait cause no open close in the same kline

    def _signal_close(self, row:dict, tp_price:Decimal, sl_price:Decimal, position_side:PositionSide):
        imax = max(tp_price, sl_price)
        imin = min(tp_price, sl_price)
        high = row["high_price"]
        low = row["low_price"]

        if imax >= high >= low >= imin:
            return SignalStatus(
                next_target=self._signal_close,
                next_kwargs={
                    "tp_price":tp_price,
                    "sl_price":sl_price,
                    "position_side":position_side
                },
                event=None
            ) # without wait doesn't effect result
        
        return SignalStatus(
            next_target = self._signal_open,
            next_kwargs = {},

            event=CloseOrder(
                position_pct=1,
                position_side=position_side,
                price=imax if high > imax else imin,
                time=row["open_time"],
                info={"close_type":"price out of bound"},
                is_final=True
            )
        ) # no wait, need open right after close

