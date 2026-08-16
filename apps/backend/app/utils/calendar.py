import datetime as dt
from typing import List, Optional

class IDXCalendar:
    """
    Indonesian Stock Exchange (IDX) Calendar Utility.
    Includes National Holidays for 2024 and 2025.
    """

    # Official IDX Holidays 2024
    HOLIDAYS_2024 = [
        dt.date(2024, 1, 1),   # Tahun Baru 2024 Masehi
        dt.date(2024, 2, 8),   # Isra Mikraj Nabi Muhammad SAW
        dt.date(2024, 2, 9),   # Cuti Bersama Tahun Baru Imlek
        dt.date(2024, 2, 10),  # Tahun Baru Imlek 2575 Kongzili
        dt.date(2024, 2, 14),  # Hari Pemilihan Umum (Pemilu)
        dt.date(2024, 3, 11),  # Hari Suci Nyepi (Tahun Baru Saka 1946)
        dt.date(2024, 3, 12),  # Cuti Bersama Hari Suci Nyepi
        dt.date(2024, 3, 29),  # Wafat Yesus Kristus
        dt.date(2024, 3, 31),  # Kebangkitan Yesus Kristus (Paskah)
        dt.date(2024, 4, 8),   # Cuti Bersama Idul Fitri 1445 H
        dt.date(2024, 4, 9),   # Cuti Bersama Idul Fitri 1445 H
        dt.date(2024, 4, 10),  # Hari Raya Idul Fitri 1445 H
        dt.date(2024, 4, 11),  # Hari Raya Idul Fitri 1445 H
        dt.date(2024, 4, 12),  # Cuti Bersama Idul Fitri 1445 H
        dt.date(2024, 4, 15),  # Cuti Bersama Idul Fitri 1445 H
        dt.date(2024, 5, 1),   # Hari Buruh Internasional
        dt.date(2024, 5, 9),   # Kenaikan Yesus Kristus
        dt.date(2024, 5, 10),  # Cuti Bersama Kenaikan Yesus Kristus
        dt.date(2024, 5, 23),  # Hari Raya Waisak 2568 BE
        dt.date(2024, 5, 24),  # Cuti Bersama Hari Raya Waisak
        dt.date(2024, 6, 1),   # Hari Lahir Pancasila
        dt.date(2024, 6, 17),  # Hari Raya Idul Adha 1445 H
        dt.date(2024, 6, 18),  # Cuti Bersama Hari Raya Idul Adha
        dt.date(2024, 7, 7),   # Tahun Baru Islam 1446 H
        dt.date(2024, 8, 17),  # Hari Kemerdekaan RI
        dt.date(2024, 9, 16),  # Maulid Nabi Muhammad SAW
        dt.date(2024, 12, 25), # Hari Raya Natal
        dt.date(2024, 12, 26), # Cuti Bersama Hari Raya Natal
    ]

    # Official IDX Holidays 2025 (Estimates based on Government decrees)
    HOLIDAYS_2025 = [
        dt.date(2025, 1, 1),   # Tahun Baru 2025 Masehi
        dt.date(2025, 1, 27),  # Isra Mikraj Nabi Muhammad SAW
        dt.date(2025, 1, 29),  # Tahun Baru Imlek 2576 Kongzili
        dt.date(2025, 3, 29),  # Hari Suci Nyepi (Tahun Baru Saka 1947)
        dt.date(2025, 3, 31),  # Hari Raya Idul Fitri 1446 H
        dt.date(2025, 4, 1),   # Hari Raya Idul Fitri 1446 H
        dt.date(2025, 4, 18),  # Wafat Yesus Kristus
        dt.date(2025, 4, 20),  # Hari Paskah
        dt.date(2025, 5, 1),   # Hari Buruh Internasional
        dt.date(2025, 5, 12),  # Hari Raya Waisak 2569 BE
        dt.date(2025, 5, 29),  # Kenaikan Yesus Kristus
        dt.date(2025, 6, 1),   # Hari Lahir Pancasila
        dt.date(2025, 6, 6),   # Hari Raya Idul Adha 1446 H
        dt.date(2025, 6, 27),  # Tahun Baru Islam 1447 H
        dt.date(2025, 8, 17),  # Hari Kemerdekaan RI
        dt.date(2025, 9, 5),   # Maulid Nabi Muhammad SAW
        dt.date(2025, 12, 25), # Hari Raya Natal
        dt.date(2025, 12, 26), # Cuti Bersama Hari Raya Natal
    ]

    ALL_HOLIDAYS = HOLIDAYS_2024 + HOLIDAYS_2025

    @classmethod
    def is_holiday(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None:
            date_val = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
        return date_val in cls.ALL_HOLIDAYS

    @classmethod
    def get_next_trading_day(cls, start_date: dt.date) -> dt.date:
        next_day = start_date + dt.timedelta(days=1)
        while next_day.weekday() >= 5 or cls.is_holiday(next_day):
            next_day += dt.timedelta(days=1)
        return next_day

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
            "is_market_open": not (wib_ts.weekday() >= 5 or cls.is_holiday(wib_ts.date())),
            "trading_day_status": "Holiday" if cls.is_holiday(wib_ts.date()) else ("Weekend" if wib_ts.weekday() >= 5 else "Open")
        }
