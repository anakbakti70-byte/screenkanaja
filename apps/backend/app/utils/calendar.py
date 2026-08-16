import datetime as dt
from typing import List, Optional

class IDXCalendar:
    """
    Indonesian Stock Exchange (IDX) Calendar Utility.
    Includes National Holidays and Cuti Bersama for 2023 - 2026.
    """

    # Official IDX Holidays 2023
    HOLIDAYS_2023 = [
        dt.date(2023, 1, 1),   # Tahun Baru
        dt.date(2023, 1, 2),   # Pengganti Libur Tahun Baru
        dt.date(2023, 1, 22),  # Tahun Baru Imlek
        dt.date(2023, 1, 23),  # Cuti Bersama Imlek
        dt.date(2023, 2, 18),  # Isra Mikraj
        dt.date(2023, 3, 22),  # Hari Raya Nyepi
        dt.date(2023, 3, 23),  # Cuti Bersama Nyepi
        dt.date(2023, 4, 7),   # Wafat Yesus Kristus
        dt.date(2023, 4, 19),  # Cuti Bersama Lebaran
        dt.date(2023, 4, 20),  # Cuti Bersama Lebaran
        dt.date(2023, 4, 21),  # Cuti Bersama Lebaran
        dt.date(2023, 4, 24),  # Cuti Bersama Lebaran
        dt.date(2023, 4, 25),  # Cuti Bersama Lebaran
        dt.date(2023, 5, 1),   # Hari Buruh
        dt.date(2023, 5, 18),  # Kenaikan Yesus Kristus
        dt.date(2023, 6, 1),   # Hari Lahir Pancasila
        dt.date(2023, 6, 2),   # Cuti Bersama Waisak
        dt.date(2023, 6, 4),   # Hari Raya Waisak
        dt.date(2023, 6, 28),  # Cuti Bersama Idul Adha
        dt.date(2023, 6, 29),  # Idul Adha
        dt.date(2023, 6, 30),  # Cuti Bersama Idul Adha
        dt.date(2023, 7, 19),  # Tahun Baru Islam
        dt.date(2023, 8, 17),  # Hari Kemerdekaan
        dt.date(2023, 9, 28),  # Maulid Nabi
        dt.date(2023, 12, 25), # Natal
        dt.date(2023, 12, 26), # Cuti Bersama Natal
    ]

    # Official IDX Holidays 2024
    HOLIDAYS_2024 = [
        dt.date(2024, 1, 1),   # Tahun Baru
        dt.date(2024, 2, 8),   # Isra Mikraj
        dt.date(2024, 2, 9),   # Cuti Bersama Imlek
        dt.date(2024, 2, 10),  # Tahun Baru Imlek
        dt.date(2024, 2, 14),  # Pemilu 2024
        dt.date(2024, 3, 11),  # Hari Raya Nyepi
        dt.date(2024, 3, 12),  # Cuti Bersama Nyepi
        dt.date(2024, 3, 29),  # Wafat Yesus Kristus
        dt.date(2024, 4, 8),   # Cuti Bersama Lebaran
        dt.date(2024, 4, 9),   # Cuti Bersama Lebaran
        dt.date(2024, 4, 10),  # Idul Fitri
        dt.date(2024, 4, 11),  # Idul Fitri
        dt.date(2024, 4, 12),  # Cuti Bersama Lebaran
        dt.date(2024, 4, 15),  # Cuti Bersama Lebaran
        dt.date(2024, 5, 1),   # Hari Buruh
        dt.date(2024, 5, 9),   # Kenaikan Yesus Kristus
        dt.date(2024, 5, 10),  # Cuti Bersama Kenaikan
        dt.date(2024, 5, 23),  # Hari Raya Waisak
        dt.date(2024, 5, 24),  # Cuti Bersama Waisak
        dt.date(2024, 6, 1),   # Hari Lahir Pancasila
        dt.date(2024, 6, 17),  # Idul Adha
        dt.date(2024, 6, 18),  # Cuti Bersama Idul Adha
        dt.date(2024, 7, 7),   # Tahun Baru Islam
        dt.date(2024, 8, 17),  # Hari Kemerdekaan
        dt.date(2024, 9, 16),  # Maulid Nabi
        dt.date(2024, 12, 25), # Natal
        dt.date(2024, 12, 26), # Cuti Bersama Natal
    ]

    # Official IDX Holidays 2025
    HOLIDAYS_2025 = [
        dt.date(2025, 1, 1),   # Tahun Baru
        dt.date(2025, 1, 27),  # Isra Mikraj
        dt.date(2025, 1, 28),  # Cuti Bersama Imlek
        dt.date(2025, 1, 29),  # Tahun Baru Imlek
        dt.date(2025, 3, 28),  # Cuti Bersama Nyepi
        dt.date(2025, 3, 29),  # Hari Raya Nyepi
        dt.date(2025, 3, 31),  # Idul Fitri
        dt.date(2025, 4, 1),   # Idul Fitri
        dt.date(2025, 4, 2),   # Cuti Bersama Lebaran
        dt.date(2025, 4, 3),   # Cuti Bersama Lebaran
        dt.date(2025, 4, 4),   # Cuti Bersama Lebaran
        dt.date(2025, 4, 7),   # Cuti Bersama Lebaran
        dt.date(2025, 4, 18),  # Wafat Yesus Kristus
        dt.date(2025, 5, 1),   # Hari Buruh
        dt.date(2025, 5, 12),  # Hari Raya Waisak
        dt.date(2025, 5, 13),  # Cuti Bersama Waisak
        dt.date(2025, 5, 29),  # Kenaikan Yesus Kristus
        dt.date(2025, 5, 30),  # Cuti Bersama Kenaikan
        dt.date(2025, 6, 1),   # Hari Lahir Pancasila
        dt.date(2025, 6, 6),   # Idul Adha
        dt.date(2025, 6, 9),   # Cuti Bersama Idul Adha
        dt.date(2025, 6, 27),  # Tahun Baru Islam
        dt.date(2025, 8, 17),  # Hari Kemerdekaan
        dt.date(2025, 9, 5),   # Maulid Nabi
        dt.date(2025, 12, 25), # Natal
        dt.date(2025, 12, 26), # Cuti Bersama Natal
    ]

    # Tentative IDX Holidays 2026 (Projections)
    HOLIDAYS_2026 = [
        dt.date(2026, 1, 1),   # Tahun Baru
        dt.date(2026, 1, 15),  # Isra Mikraj (Estimate)
        dt.date(2026, 2, 17),  # Tahun Baru Imlek (Estimate)
        dt.date(2026, 3, 19),  # Hari Raya Nyepi (Estimate)
        dt.date(2026, 3, 20),  # Idul Fitri (Estimate)
        dt.date(2026, 3, 21),  # Idul Fitri (Estimate)
        dt.date(2026, 4, 3),   # Wafat Yesus Kristus
        dt.date(2026, 5, 1),   # Hari Buruh
        dt.date(2026, 5, 14),  # Kenaikan Yesus Kristus (Estimate)
        dt.date(2026, 5, 31),  # Hari Raya Waisak (Estimate)
        dt.date(2026, 6, 1),   # Hari Lahir Pancasila
        dt.date(2026, 6, 26),  # Idul Adha (Estimate)
        dt.date(2026, 7, 16),  # Tahun Baru Islam (Estimate)
        dt.date(2026, 8, 17),  # Hari Kemerdekaan
        dt.date(2026, 8, 25),  # Maulid Nabi (Estimate)
        dt.date(2026, 12, 25), # Natal
        dt.date(2026, 12, 26), # Cuti Bersama Natal
    ]

    ALL_HOLIDAYS = HOLIDAYS_2023 + HOLIDAYS_2024 + HOLIDAYS_2025 + HOLIDAYS_2026

    @classmethod
    def is_holiday(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None:
            # Default to WIB
            date_val = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
        return date_val in cls.ALL_HOLIDAYS

    @classmethod
    def is_trading_day(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None:
            date_val = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()

        # Weekend
        if date_val.weekday() >= 5:
            return False

        # Holiday
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
        """
        Enriches a timestamp with trading context (week, day name, session).
        """
        # Convert to WIB
        wib_ts = timestamp.astimezone(dt.timezone(dt.timedelta(hours=7)))

        return {
            "day_name": wib_ts.strftime('%A'),
            "week_number": wib_ts.isocalendar()[1],
            "is_market_open": cls.is_trading_day(wib_ts.date()),
            "status": "Holiday" if cls.is_holiday(wib_ts.date()) else ("Weekend" if wib_ts.weekday() >= 5 else "Trading Day")
        }
