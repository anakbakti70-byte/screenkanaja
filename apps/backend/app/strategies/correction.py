import pandas as pd
from typing import Dict, Optional

from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.fibonacci.extension import calculate_fib_extension
from app.confirmation.candle import check_bullish_candle
from app.strategies.bullish_divergence import _find_confirming_indicator


class CorrectionStrategy(BaseStrategy):
    """
    final.md §4: Correction (ABC).

    Dipakai SETELAH bullish divergence pertama kena TP -- entry kedua di
    titik koreksi (pullback) sebelum lanjut naik. Titik A = puncak setelah TP
    bullish div pertama (approx = high setelah low bullish-div, dipakai sbg
    "TP high"), turun ke B/C = zona koreksi saat ini.

    Syarat WAJIB (§4.1-§4.3, Varian A -- confluence penuh Varian B opsional
    sebagai penguat, ditandai di metadata):
    1. Ada leg bullish-div-1 (low) -> TP high (high) yang sudah terbentuk.
    2. Harga masuk zona tunggu Fib 0.6/0.7 dari leg tsb (retracement turun, §4.2).
    3. Candle konfirmasi valid (§3.3 -- sama syaratnya di semua metode).
    4. (Confluence tambahan, opsional/Varian B) ada bullish divergence lagi di
       zona koreksi (dicek lewat indikator, bukan wajib -- "sangat direkomendasikan").

    SL = low bullish divergence SEBELUMNYA (§4.3 Varian A) -- SL PALING JAUH
    dari ketiga metode (trade-off risk/reward terbesar, §4.4).
    TP = fib extension 1.618, dari leg (low bulldiv1 -> TP high) diproyeksikan
    ke low correction saat ini (§4.4), syarat breakout minimal Fib 1.2 dari TP high.
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Correction (ABC)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        lows = pivots[pivots["type"] == -1]
        highs = pivots[pivots["type"] == 1]
        if len(lows) < 2 or highs.empty:
            return None

        # Low bullish-div-1 = low sebelum leg naik ke TP high (dua low terakhir
        # dipakai supaya leg "bulldiv_low -> tp_high" adalah leg NAIK paling baru).
        bulldiv_low = lows.iloc[-2]
        tp_high = highs.iloc[-1]
        correction_low = lows.iloc[-1]  # low koreksi saat ini (titik C)

        # Leg bulldiv_low -> tp_high harus benar-benar leg naik & dalam urutan waktu yang benar
        if not (tp_high["index"] > bulldiv_low["index"] and correction_low["index"] > tp_high["index"]):
            return None
        if not (tp_high["price"] > bulldiv_low["price"] and correction_low["price"] < tp_high["price"]):
            return None

        # Rule §4.2: zona tunggu Fib 0.6/0.7, retracement TURUN dari tp_high
        # menuju bulldiv_low.
        wait_zone = calculate_fib_levels(start=bulldiv_low["price"], end=tp_high["price"], levels=[0.6, 0.7])
        current_price = float(df["Close"].iloc[-1])

        # level 0.6 (lebih dekat ke high) > level 0.7 (lebih dekat ke low) secara harga
        zone_high, zone_low = wait_zone[0.6], wait_zone[0.7]
        if not (zone_low <= current_price <= zone_high):
            return None

        if not check_bullish_candle(df):
            return None

        # Varian B (confluence penuh, §4.3): cek apakah ADA bullish divergence
        # tambahan di zona koreksi (indikator higher-low antara tp_high dan
        # correction_low). Ini opsional/penguat, bukan syarat wajib (§4.1:
        # "opsional tapi sangat direkomendasikan").
        confluence_indicator = _find_confirming_indicator(indicators, int(tp_high["index"]), int(correction_low["index"]))
        variant = "B_full_confluence" if confluence_indicator else "A_strict_invalidation"

        # Rule §4.3:
        #   Varian A: SL = low bullish divergence SEBELUMNYA (bulldiv_low)
        #   Varian B: SL = low invalidation dari pola bullish div di zona koreksi
        #             (di sini didekati dengan correction_low, karena itulah low
        #             invalidation pola divergence baru yang terbentuk di zona koreksi)
        sl_price = float(correction_low["price"]) if confluence_indicator else float(bulldiv_low["price"])

        # Rule §4.4: TP = fib extension 1.618, leg (bulldiv_low -> tp_high)
        # diproyeksikan dari correction_low (titik C).
        tp_ext = calculate_fib_extension(point_a=float(bulldiv_low["price"]), point_b=float(tp_high["price"]),
                                          point_c=float(correction_low["price"]), levels=[1.618])
        tp_price = tp_ext[1.618]

        # Syarat breakout minimal Fib 1.2 dari tp_high (§4.4) -- extension leg
        # (bulldiv_low -> tp_high) diproyeksikan dari tp_high itu sendiri.
        # Dicatat di metadata sebagai syarat yang harus dipantau setelah entry
        # (breakout terjadi SETELAH entry, sama logikanya dengan tp_far di
        # Double Bullish Divergence), bukan dicek di titik entry ini.
        breakout_min = calculate_fib_extension(point_a=float(bulldiv_low["price"]), point_b=float(tp_high["price"]),
                                                point_c=float(tp_high["price"]), levels=[1.2])[1.2]

        risk = current_price - sl_price
        reward = tp_price - current_price
        if risk <= 0:
            return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "bulldiv_low": {"idx": int(bulldiv_low["index"]), "price": float(bulldiv_low["price"])},
                "tp_high": {"idx": int(tp_high["index"]), "price": float(tp_high["price"])},
                "correction_low": {"idx": int(correction_low["index"]), "price": float(correction_low["price"])},
            },
            "fib_levels": {"wait_zone": {str(k): v for k, v in wait_zone.items()},
                            "tp_extension_1618": tp_price,
                            "breakout_min_fib_1_2": breakout_min},
            "variant": variant,
            "confluence_indicator": confluence_indicator,
        }

        return SetupResult(
            status="READY",
            strategy_name=self.name,
            symbol=df.attrs.get("symbol", "UNKNOWN"),
            timeframe=df.attrs.get("timeframe", "UNKNOWN"),
            entry_price=current_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            risk_reward=rr,
            score=rr * 10,
            metadata=plot_data,
        )
