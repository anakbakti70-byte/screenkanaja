import datetime as dt
from typing import List, Optional

class IDXCalendar:
    """
    Indonesian Stock Exchange (IDX) Calendar Utility.
    Includes National Holidays and Cuti Bersama for 2023 - 2026.
    """

    # Official IDX Holidays 2023
    HOLIDAYS_2023 = [
        dt.date(2023, 1, 1), dt.date(2023, 1, 2), dt.date(2023, 1, 22), dt.date(2023, 1, 23),
        dt.date(2023, 2, 18), dt.date(2023, 3, 22), dt.date(2023, 3, 23), dt.date(2023, 4, 7),
        dt.date(2023, 4, 19), dt.date(2023, 4, 20), dt.date(2023, 4, 21), dt.date(2023, 4, 24),
        dt.date(2023, 4, 25), dt.date(2023, 5, 1), dt.date(2023, 5, 18), dt.date(2023, 6, 1),
        dt.date(2023, 6, 2), dt.date(2023, 6, 4), dt.date(2023, 6, 28), dt.date(2023, 6, 29),
        dt.date(2023, 6, 30), dt.date(2023, 7, 19), dt.date(2023, 8, 17), dt.date(2023, 9, 28),
        dt.date(2023, 12, 25), dt.date(2023, 12, 26),
    ]

    # Official IDX Holidays 2024
    HOLIDAYS_2024 = [
        dt.date(2024, 1, 1), dt.date(2024, 2, 8), dt.date(2024, 2, 9), dt.date(2024, 2, 10),
        dt.date(2024, 2, 14), dt.date(2024, 3, 11), dt.date(2024, 3, 12), dt.date(2024, 3, 29),
        dt.date(2024, 4, 8), dt.date(2024, 4, 9), dt.date(2024, 4, 10), dt.date(2024, 4, 11),
        dt.date(2024, 4, 12), dt.date(2024, 4, 15), dt.date(2024, 5, 1), dt.date(2024, 5, 9),
        dt.date(2024, 5, 10), dt.date(2024, 5, 23), dt.date(2024, 5, 24), dt.date(2024, 6, 1),
        dt.date(2024, 6, 17), dt.date(2024, 6, 18), dt.date(2024, 7, 7), dt.date(2024, 8, 17),
        dt.date(2024, 9, 16), dt.date(2024, 12, 25), dt.date(2024, 12, 26),
    ]

    # Official IDX Holidays 2025
    HOLIDAYS_2025 = [
        dt.date(2025, 1, 1), dt.date(2025, 1, 27), dt.date(2025, 1, 28), dt.date(2025, 1, 29),
        dt.date(2025, 3, 28), dt.date(2025, 3, 29), dt.date(2025, 3, 31), dt.date(2025, 4, 1),
        dt.date(2025, 4, 2), dt.date(2025, 4, 3), dt.date(2025, 4, 4), dt.date(2025, 4, 7),
        dt.date(2025, 4, 18), dt.date(2025, 5, 1), dt.date(2025, 5, 12), dt.date(2025, 5, 13),
        dt.date(2025, 5, 29), dt.date(2025, 5, 30), dt.date(2025, 6, 1), dt.date(2025, 6, 6),
        dt.date(2025, 6, 9), dt.date(2025, 6, 27), dt.date(2025, 8, 17), dt.date(2025, 9, 5),
        dt.date(2025, 12, 25), dt.date(2025, 12, 26),
    ]

    # Tentative IDX Holidays 2026 (Estimates + Guaranteed Fixed Dates)
    HOLIDAYS_2026 = [
        dt.date(2026, 1, 1),   # Tahun Baru
        dt.date(2026, 1, 15),  # Isra Mikraj (Est)
        dt.date(2026, 2, 17),  # Tahun Baru Imlek (Est)
        dt.date(2026, 3, 19),  # Hari Raya Nyepi (Est)
        dt.date(2026, 3, 20),  # Idul Fitri (Est)
        dt.date(2026, 3, 21),  # Idul Fitri (Est)
        dt.date(2026, 4, 3),   # Wafat Yesus Kristus
        dt.date(2026, 5, 1),   # Hari Buruh
        dt.date(2026, 5, 14),  # Kenaikan Yesus Kristus (Est)
        dt.date(2026, 5, 31),  # Hari Raya Waisak (Est)
        dt.date(2026, 6, 1),   # Hari Lahir Pancasila
        dt.date(2026, 6, 26),  # Idul Adha (Est)
        dt.date(2026, 7, 16),  # Tahun Baru Islam (Est)
        dt.date(2026, 8, 17),  # Hari Kemerdekaan RI (FIXED)
        dt.date(2026, 8, 25),  # Maulid Nabi (Est)
        dt.date(2026, 12, 25), # Natal
        dt.date(2026, 12, 26), # Cuti Bersama Natal
    ]

    # COMBINE ALL YEARS
    ALL_HOLIDAYS = sorted(list(set(
        HOLIDAYS_2023 + HOLIDAYS_2024 + HOLIDAYS_2025 + HOLIDAYS_2026
    )))

    @classmethod
    def is_holiday(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None:
            date_val = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
        return date_val in cls.ALL_HOLIDAYS

    @classmethod
    def is_trading_day(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None:
            date_val = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
        if date_val.weekday() >= 5: # Sat, Sun
            return False
        if cls.is_holiday(date_val):
            return False
        return True

    @classmethod
    def get_next_trading_day(cls, start_date: dt.date) -> dt.date:
        next_day = start_date + dt.timedelta(days=1)
        while not cls.is_trading_day(next_day):
            next_day += dt.timedelta(days=1)
        return next_day

    @classmethod
    def get_prev_trading_day(cls, start_date: dt.date) -> dt.date:
        prev_day = start_date - dt.timedelta(days=1)
        while not cls.is_trading_day(prev_day):
            prev_day -= dt.timedelta(days=1)
        return prev_day

    @classmethod
    def get_trading_context(cls, timestamp: dt.datetime) -> dict:
        wib_ts = timestamp.astimezone(dt.timezone(dt.timedelta(hours=7)))
        date_val = wib_ts.date()
        return {
            "day_name": wib_ts.strftime('%A'),
            "week_number": wib_ts.isocalendar()[1],
            "is_trading_day": cls.is_trading_day(date_val),
            "status": "Holiday" if cls.is_holiday(date_val) else ("Weekend" if date_val.weekday() >= 5 else "Trading Day")
        }
