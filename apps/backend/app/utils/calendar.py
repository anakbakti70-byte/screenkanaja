import datetime as dt
from typing import List, Optional

class IDXCalendar:
    """
    Indonesian Stock Exchange (IDX) Calendar Utility.
    Includes National Holidays and Cuti Bersama for 2024 and 2025.
    """

    # Official IDX Holidays 2024
    # Source: https://www.idx.co.id/en-us/about-idx/holiday-calendar/
    HOLIDAYS_2024 = [
        dt.date(2024, 1, 1),   # New Year's Day
        dt.date(2024, 2, 8),   # Isra Mi'raj of Prophet Muhammad SAW
        dt.date(2024, 2, 9),   # Joint Holiday (Chinese New Year)
        dt.date(2024, 2, 10),  # Chinese New Year 2575 Kongzili
        dt.date(2024, 2, 14),  # General Election
        dt.date(2024, 3, 11),  # Hari Suci Nyepi (Saka New Year 1946)
        dt.date(2024, 3, 12),  # Joint Holiday (Saka New Year)
        dt.date(2024, 3, 29),  # Good Friday
        dt.date(2024, 4, 8),   # Joint Holiday (Eid Al-Fitr 1445H)
        dt.date(2024, 4, 9),   # Joint Holiday (Eid Al-Fitr 1445H)
        dt.date(2024, 4, 10),  # Eid Al-Fitr 1445H
        dt.date(2024, 4, 11),  # Eid Al-Fitr 1445H
        dt.date(2024, 4, 12),  # Joint Holiday (Eid Al-Fitr 1445H)
        dt.date(2024, 4, 15),  # Joint Holiday (Eid Al-Fitr 1445H)
        dt.date(2024, 5, 1),   # International Labor Day
        dt.date(2024, 5, 9),   # Ascension Day of Jesus Christ
        dt.date(2024, 5, 10),  # Joint Holiday (Ascension Day)
        dt.date(2024, 5, 23),  # Waisak Day 2568 BE
        dt.date(2024, 5, 24),  # Joint Holiday (Waisak Day)
        dt.date(2024, 6, 1),   # Pancasila Day
        dt.date(2024, 6, 17),  # Eid Al-Adha 1445H
        dt.date(2024, 6, 18),  # Joint Holiday (Eid Al-Adha 1445H)
        dt.date(2024, 7, 7),   # Islamic New Year 1446H
        dt.date(2024, 8, 17),  # Independence Day of RI
        dt.date(2024, 9, 16),  # Birthday of Prophet Muhammad SAW
        dt.date(2024, 12, 25), # Christmas Day
        dt.date(2024, 12, 26), # Joint Holiday (Christmas Day)
    ]

    # Official IDX Holidays 2025
    # Source: Government Decree (SKB 3 Menteri)
    HOLIDAYS_2025 = [
        dt.date(2025, 1, 1),   # Tahun Baru 2025 Masehi
        dt.date(2025, 1, 27),  # Isra Mikraj Nabi Muhammad SAW
        dt.date(2025, 1, 28),  # Cuti Bersama Tahun Baru Imlek
        dt.date(2025, 1, 29),  # Tahun Baru Imlek 2576 Kongzili
        dt.date(2025, 3, 28),  # Cuti Bersama Hari Suci Nyepi
        dt.date(2025, 3, 29),  # Hari Suci Nyepi (Tahun Baru Saka 1947)
        dt.date(2025, 3, 31),  # Hari Raya Idul Fitri 1446 H
        dt.date(2025, 4, 1),   # Hari Raya Idul Fitri 1446 H
        dt.date(2025, 4, 2),   # Cuti Bersama Idul Fitri 1446 H
        dt.date(2025, 4, 3),   # Cuti Bersama Idul Fitri 1446 H
        dt.date(2025, 4, 4),   # Cuti Bersama Idul Fitri 1446 H
        dt.date(2025, 4, 7),   # Cuti Bersama Idul Fitri 1446 H
        dt.date(2025, 4, 18),  # Wafat Yesus Kristus
        dt.date(2025, 5, 1),   # Hari Buruh Internasional
        dt.date(2025, 5, 12),  # Hari Raya Waisak 2569 BE
        dt.date(2025, 5, 13),  # Cuti Bersama Hari Raya Waisak
        dt.date(2025, 5, 29),  # Kenaikan Yesus Kristus
        dt.date(2025, 5, 30),  # Cuti Bersama Kenaikan Yesus Kristus
        dt.date(2025, 6, 1),   # Hari Lahir Pancasila
        dt.date(2025, 6, 6),   # Hari Raya Idul Adha 1446 H
        dt.date(2025, 6, 9),   # Cuti Bersama Hari Raya Idul Adha
        dt.date(2025, 6, 27),  # Tahun Baru Islam 1447 H
        dt.date(2025, 8, 17),  # Hari Kemerdekaan RI
        dt.date(2025, 9, 5),   # Maulid Nabi Muhammad SAW
        dt.date(2025, 12, 25), # Hari Raya Natal
        dt.date(2025, 12, 26), # Cuti Bersama Hari Raya Natal
    ]

    ALL_HOLIDAYS = sorted(list(set(HOLIDAYS_2024 + HOLIDAYS_2025)))

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
        Enriches a timestamp with trading context (week, day name, status).
        """
        # Convert to WIB
        wib_ts = timestamp.astimezone(dt.timezone(dt.timedelta(hours=7)))
        date_val = wib_ts.date()

        return {
            "day_name": wib_ts.strftime('%A'),
            "week_number": wib_ts.isocalendar()[1],
            "is_market_open": cls.is_trading_day(date_val),
            "status": "Holiday" if cls.is_holiday(date_val) else ("Weekend" if date_val.weekday() >= 5 else "Open")
        }
