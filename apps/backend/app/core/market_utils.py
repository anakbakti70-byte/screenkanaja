import math
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, time as dt_time

@dataclass(frozen=True)
class TickRegime:
    effective_from: dt.date
    bands: tuple

TICK_REGIMES = (
    TickRegime(
        effective_from=dt.date(2000, 1, 1),
        bands=((200, 1), (500, 2), (2000, 5), (5000, 10), (None, 25))
    ),
)

@dataclass(frozen=True)
class Fees:
    buy_pct: float = 0.0019
    sell_pct: float = 0.0029
    slippage_pct: float = 0.001

    @property
    def total_sell_pct(self) -> float:
        return self.sell_pct

def tick_size(price: float, date: dt.date = None) -> int:
    for upper, tick in TICK_REGIMES[-1].bands:
        if upper is None or price < upper: return tick
    return 25

def round_to_tick(price: float, date: dt.date = None, mode: str = "nearest") -> int:
    # Logic moved here from scanner_core to become source of truth
    if price is None or price <= 0: return 50 # Harga Min
    tick = tick_size(price, date)
    ratio = price / tick
    if mode == "down": steps = math.floor(ratio + 1e-9)
    elif mode == "up": steps = math.ceil(ratio - 1e-9)
    else: steps = math.floor(ratio + 0.5 + 1e-9)
    return max(int(steps * tick), 50)

def auto_reject_bounds(prev_close: float, date: dt.date = None) -> tuple[int, int]:
    if prev_close < 200: ara, arb = 0.35, 0.35
    elif prev_close <= 5000: ara, arb = 0.25, 0.25
    else: ara, arb = 0.20, 0.20
    return round_to_tick(prev_close * (1 - arb), date, "up"), round_to_tick(prev_close * (1 + ara), date, "down")

def is_ara(price: float, prev_close: float, date: dt.date = None) -> bool:
    _, ara_p = auto_reject_bounds(prev_close, date)
    return price >= ara_p

def is_arb(price: float, prev_close: float, date: dt.date = None) -> bool:
    arb_p, _ = auto_reject_bounds(prev_close, date)
    return price <= arb_p
