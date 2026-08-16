import math
import datetime as dt
from dataclasses import dataclass
from .calendar import IDXCalendar

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
    if prev_close < 200:
        ara = 0.35
        arb = 0.35
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

def is_idx_market_open() -> bool:
    """
    Checks if IDX market is currently open based on EXACT user requirements:
    - Pra-pembukaan: 08:45:00 – 08:59:59
    - Sesi I: 09:00:00 – 12:00:00 (Jumat s/d 11:30:00)
    - Istirahat: 12:00:01 – 13:29:59 (Jumat 11:30:01 – 13:59:59)
    - Sesi II: 13:30:00 – 15:49:59 (Jumat 14:00:00 – 15:49:59)
    - Pra-penutupan: 15:50:00 – 16:00:59
    - Pasca-penutupan: 16:02:00 – 16:15:00
    """
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))) # WIB (UTC+7)
    day = now.weekday() # 0=Mon, 4=Fri
    current_time = now.time()

    # 1. Weekend and Holiday Check
    if not IDXCalendar.is_trading_day(now.date()):
        return False

    # 2. Detailed Session Check
    # Pra-pembukaan (All days)
    if dt.time(8, 45, 0) <= current_time <= dt.time(8, 59, 59):
        return True

    # Monday - Thursday
    if day <= 3:
        # Sesi I
        if dt.time(9, 0, 0) <= current_time <= dt.time(12, 0, 0):
            return True
        # Sesi II
        if dt.time(13, 30, 0) <= current_time <= dt.time(15, 49, 59):
            return True

    # Friday
    elif day == 4:
        # Sesi I
        if dt.time(9, 0, 0) <= current_time <= dt.time(11, 30, 0):
            return True
        # Sesi II
        if dt.time(14, 0, 0) <= current_time <= dt.time(15, 49, 59):
            return True

    # Pra-penutupan (All days)
    if dt.time(15, 50, 0) <= current_time <= dt.time(16, 0, 59):
        return True

    # Pasca-penutupan (All days)
    if dt.time(16, 2, 0) <= current_time <= dt.time(16, 15, 0):
        return True

    return False

@dataclass(frozen=True)
class Fees:
    buy_pct: float = 0.0019
    sell_pct: float = 0.0029
    slippage_pct: float = 0.001

    @property
    def total_sell_pct(self) -> float:
        return self.sell_pct

def apply_fees_and_slippage(price: float, side: str, fees: Fees) -> float:
    if side == "buy":
        return price * (1 + fees.buy_pct + fees.slippage_pct)
    else:
        return price * (1 - fees.sell_pct - fees.slippage_pct)
