import math
import datetime as dt
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, time as dt_time

# ==============================================================================
# PART 1: IDX CALENDAR
# ==============================================================================

class IDXCalendar:
    """Indonesian Stock Exchange (IDX) Calendar Utility 2023 - 2026."""
    HOLIDAYS_2023 = [dt.date(2023, 1, 1), dt.date(2023, 1, 2), dt.date(2023, 1, 22), dt.date(2023, 1, 23),
                     dt.date(2023, 2, 18), dt.date(2023, 3, 22), dt.date(2023, 3, 23), dt.date(2023, 4, 7),
                     dt.date(2023, 4, 19), dt.date(2023, 4, 20), dt.date(2023, 4, 21), dt.date(2023, 4, 24),
                     dt.date(2023, 4, 25), dt.date(2023, 5, 1), dt.date(2023, 5, 18), dt.date(2023, 6, 1),
                     dt.date(2023, 6, 2), dt.date(2023, 6, 4), dt.date(2023, 6, 28), dt.date(2023, 6, 29),
                     dt.date(2023, 6, 30), dt.date(2023, 7, 19), dt.date(2023, 8, 17), dt.date(2023, 9, 28),
                     dt.date(2023, 12, 25), dt.date(2023, 12, 26)]

    HOLIDAYS_2024 = [dt.date(2024, 1, 1), dt.date(2024, 2, 8), dt.date(2024, 2, 9), dt.date(2024, 2, 10),
                     dt.date(2024, 2, 14), dt.date(2024, 3, 11), dt.date(2024, 3, 12), dt.date(2024, 3, 29),
                     dt.date(2024, 4, 8), dt.date(2024, 4, 9), dt.date(2024, 4, 10), dt.date(2024, 4, 11),
                     dt.date(2024, 4, 12), dt.date(2024, 4, 15), dt.date(2024, 5, 1), dt.date(2024, 5, 9),
                     dt.date(2024, 5, 10), dt.date(2024, 5, 23), dt.date(2024, 5, 24), dt.date(2024, 6, 1),
                     dt.date(2024, 6, 17), dt.date(2024, 6, 18), dt.date(2024, 7, 7), dt.date(2024, 8, 17),
                     dt.date(2024, 9, 16), dt.date(2024, 12, 25), dt.date(2024, 12, 26)]

    HOLIDAYS_2025 = [dt.date(2025, 1, 1), dt.date(2025, 1, 27), dt.date(2025, 1, 28), dt.date(2025, 1, 29),
                     dt.date(2025, 3, 28), dt.date(2025, 3, 29), dt.date(2025, 3, 31), dt.date(2025, 4, 1),
                     dt.date(2025, 4, 2), dt.date(2025, 4, 3), dt.date(2025, 4, 4), dt.date(2025, 4, 7),
                     dt.date(2025, 4, 18), dt.date(2025, 5, 1), dt.date(2025, 5, 12), dt.date(2025, 5, 13),
                     dt.date(2025, 5, 29), dt.date(2025, 5, 30), dt.date(2025, 6, 1), dt.date(2025, 6, 6),
                     dt.date(2025, 6, 9), dt.date(2025, 6, 27), dt.date(2025, 8, 17), dt.date(2025, 9, 5),
                     dt.date(2025, 12, 25), dt.date(2025, 12, 26)]

    HOLIDAYS_2026 = [dt.date(2026, 1, 1), dt.date(2026, 1, 15), dt.date(2026, 2, 17), dt.date(2026, 3, 19),
                     dt.date(2026, 3, 20), dt.date(2026, 3, 21), dt.date(2026, 4, 3), dt.date(2026, 5, 1),
                     dt.date(2026, 5, 14), dt.date(2026, 5, 31), dt.date(2026, 6, 1), dt.date(2026, 6, 26),
                     dt.date(2026, 7, 16), dt.date(2026, 8, 17), dt.date(2026, 8, 25), dt.date(2026, 12, 25),
                     dt.date(2026, 12, 26)]

    ALL_HOLIDAYS = sorted(list(set(HOLIDAYS_2023 + HOLIDAYS_2024 + HOLIDAYS_2025 + HOLIDAYS_2026)))

    @classmethod
    def is_holiday(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None: date_val = datetime.now(timezone(dt.timedelta(hours=7))).date()
        return date_val in cls.ALL_HOLIDAYS

    @classmethod
    def is_trading_day(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None: date_val = datetime.now(timezone(dt.timedelta(hours=7))).date()
        return date_val.weekday() < 5 and not cls.is_holiday(date_val)

    @classmethod
    def get_next_trading_day(cls, start_date: dt.date) -> dt.date:
        next_day = start_date + dt.timedelta(days=1)
        while not cls.is_trading_day(next_day): next_day += dt.timedelta(days=1)
        return next_day

    @classmethod
    def get_trading_context(cls, timestamp: datetime) -> dict:
        wib_ts = timestamp.astimezone(timezone(dt.timedelta(hours=7)))
        date_val = wib_ts.date()
        return {"day_name": wib_ts.strftime('%A'), "week_number": wib_ts.isocalendar()[1],
                "is_trading_day": cls.is_trading_day(date_val),
                "status": "Holiday" if cls.is_holiday(date_val) else ("Weekend" if date_val.weekday() >= 5 else "Trading Day")}

# ==============================================================================
# PART 2: MARKET RULES
# ==============================================================================

LOT, HARGA_MIN = 100, 50

@dataclass(frozen=True)
class TickRegime:
    effective_from: dt.date
    bands: tuple

TICK_REGIMES = (TickRegime(effective_from=dt.date(2000, 1, 1), bands=((200, 1), (500, 2), (2000, 5), (5000, 10), (None, 25))),)

def tick_size(price: float, date: dt.date = None) -> int:
    for upper, tick in TICK_REGIMES[-1].bands:
        if upper is None or price < upper: return tick
    return 25

def round_to_tick(price: float, date: dt.date = None, mode: str = "nearest") -> int:
    if price <= 0: return HARGA_MIN
    tick = tick_size(price, date)
    ratio = price / tick
    steps = math.floor(ratio + 1e-9) if mode == "down" else (math.ceil(ratio - 1e-9) if mode == "up" else math.floor(ratio + 0.5 + 1e-9))
    return max(int(steps * tick), HARGA_MIN)

def is_idx_market_open() -> bool:
    """Exact IDX schedule: 08:45 pre-opening, 09:00-12:00, 13:30-16:15."""
    now = datetime.now(timezone(dt.timedelta(hours=7)))
    day, current_time = now.weekday(), now.time()
    if not IDXCalendar.is_trading_day(now.date()): return False

    if day <= 3: # Mon-Thu
        s1, s2 = (dt_time(8, 45), dt_time(12, 0)), (dt_time(13, 30), dt_time(16, 15))
    elif day == 4: # Fri
        s1, s2 = (dt_time(8, 45), dt_time(11, 30)), (dt_time(14, 0), dt_time(16, 15))
    else: return False

    if (s1[0] <= current_time <= s1[1]) or (s2[0] <= current_time <= s2[1]):
        if dt_time(16, 1) <= current_time < dt_time(16, 2): return False
        return True
    return False

@dataclass(frozen=True)
class Fees:
    buy_pct: float = 0.0019
    sell_pct: float = 0.0029
    slippage_pct: float = 0.001

def auto_reject_bounds(prev_close: float, date: dt.date = None) -> tuple[int, int]:
    if prev_close < 200:
        ara, arb = 0.35, 0.35
    elif prev_close <= 5000:
        ara, arb = 0.25, 0.25
    else:
        ara, arb = 0.20, 0.20
    lower_raw = prev_close * (1 - arb)
    upper_raw = prev_close * (1 + ara)
    return round_to_tick(lower_raw, date, "up"), round_to_tick(upper_raw, date, "down")

def is_ara(price: float, prev_close: float, date: dt.date = None) -> bool:
    _, ara_price = auto_reject_bounds(prev_close, date)
    return price >= ara_price

def is_arb(price: float, prev_close: float, date: dt.date = None) -> bool:
    arb_price, _ = auto_reject_bounds(prev_close, date)
    return price <= arb_price
