import math
import datetime as dt
from dataclasses import dataclass

LOT = 100
HARGA_MIN = 50

@dataclass(frozen=True)
class TickRegime:
    effective_from: dt.date
    bands: tuple # (batas_atas_eksklusif, fraksi)

TICK_REGIMES = (
    TickRegime(
        effective_from=dt.date(2000, 1, 1),
        bands=((200, 1), (500, 2), (2000, 5), (5000, 10), (None, 25)),
    ),
)

def tick_size(price: float, date: dt.date = None) -> int:
    if price < 0: return 1
    # Simple implementation based on latest regime for now
    for upper, tick in TICK_REGIMES[-1].bands:
        if upper is None or price < upper:
            return tick
    return 25

def round_to_tick(price: float, date: dt.date = None, mode: str = "nearest") -> int:
    if price <= 0: return HARGA_MIN

    tick = tick_size(price, date)
    ratio = price / tick
    if mode == "down":
        steps = math.floor(ratio + 1e-9)
    elif mode == "up":
        steps = math.ceil(ratio - 1e-9)
    else:
        steps = math.floor(ratio + 0.5 + 1e-9)

    return max(int(steps * tick), HARGA_MIN)

def auto_reject_bounds(prev_close: float, date: dt.date = None) -> tuple[int, int]:
    # Simplified modern IDX rules
    if prev_close < 200:
        ara = 0.35
        arb = 0.35 # Simplified: matching modern ARB symmetrical rules or 15% as per transition
    elif prev_close <= 5000:
        ara = 0.25
        arb = 0.25
    else:
        ara = 0.20
        arb = 0.20

    lower_raw = prev_close * (1 - arb)
    upper_raw = prev_close * (1 + ara)

    return round_to_tick(lower_raw, date, "up"), round_to_tick(upper_raw, date, "down")

def is_ara(price: float, prev_close: float, date: dt.date = None) -> bool:
    _, ara_price = auto_reject_bounds(prev_close, date)
    return price >= ara_price

def is_arb(price: float, prev_close: float, date: dt.date = None) -> bool:
    arb_price, _ = auto_reject_bounds(prev_close, date)
    return price <= arb_price

from .calendar import IDXCalendar

def is_idx_market_open() -> bool:
    """
    Checks if IDX market is currently open based on user requirements:
    - Monday to Friday (0-4)
    - 08:45 - 12:00
    - 12:55 - 17:00
    - Saturday, Sunday, and National Holidays (Automatic via IDXCalendar)
    """
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))) # WIB (UTC+7)
    day = now.weekday()
    current_time = now.time()

    # 1. Check Weekend (Saturday=5, Sunday=6)
    if day >= 5:
        return False

    # 2. Check National Holidays
    if IDXCalendar.is_holiday(now.date()):
        return False

    # 3. Check Market Hours
    session1_start = dt.time(8, 45)
    session1_end = dt.time(12, 0)
    session2_start = dt.time(12, 55)
    session2_end = dt.time(17, 0)

    is_session1 = session1_start <= current_time <= session1_end
    is_session2 = session2_start <= current_time <= session2_end

    return is_session1 or is_session2

@dataclass(frozen=True)
class Fees:
    buy_pct: float = 0.0019 # Conservative default
    sell_pct: float = 0.0029 # Conservative default
    slippage_pct: float = 0.001 # 0.1% slippage

    @property
    def total_sell_pct(self) -> float:
        """Alias for engine compatibility, including PPh if necessary."""
        return self.sell_pct

def apply_fees_and_slippage(price: float, side: str, fees: Fees) -> float:
    if side == "buy":
        return price * (1 + fees.buy_pct + fees.slippage_pct)
    else:
        return price * (1 - fees.sell_pct - fees.slippage_pct)
