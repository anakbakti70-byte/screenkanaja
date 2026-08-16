import pandas as pd
from typing import Dict, Optional

from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.confirmation.candle import check_bullish_candle

INDICATOR_PRIORITY = ["AO", "MACD", "RSI"]  # final.md §2: urutan cek AO -> MACD -> RSI


def _find_confirming_indicator(indicators: Dict[str, pd.Series], idx_low: int, idx_high: int) -> Optional[str]:
    """
    Cek final.md §2: cukup SATU dari RSI/MACD/AO yang membentuk higher-low
    (nilai di idx_high > nilai di idx_low) untuk dianggap divergence confirm.
    idx_low = index pivot yang lebih dulu (lebih rendah harganya di price),
    idx_high = index pivot yang lebih baru.
    """
    for name in INDICATOR_PRIORITY:
        series = indicators.get(name)
        if series is None or series.empty:
            continue
        if idx_low >= len(series) or idx_high >= len(series):
            continue
        if series.iloc[idx_high] > series.iloc[idx_low]:
            return name
    return None


class BullishDivergenceStrategy(BaseStrategy):
    """
    final.md §3: Bullish Divergence (Regular).

    Syarat WAJIB (§3.1-§3.3), SEMUA harus terpenuhi:
    1. Struktur 5 wave turun lengkap (W1-W2-W3-W4-W5), wave-3 = penurunan terpanjang.
    2. Harga membuat lower-low: W5 < W3 (§3.1).
    3. Minimal satu indikator (AO/MACD/RSI) higher-low di W5 vs W3 (§2).
    4. Candle konfirmasi hijau berbadan, bukan doji (§3.3 poin 1, cek di
       app/confirmation/candle.py).

    SL = low candle konfirmasi (termasuk wick, §3.4).
    TP = Fibonacci retracement HIGH(W4) -> LOW(W5), target minimal 0.6 (§3.5).
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if pivots.empty or "movement_label" not in pivots.columns:
            return None

        w5_rows = pivots[pivots["movement_label"] == "W5"]
        if w5_rows.empty:
            return None

        w5 = w5_rows.iloc[-1]
        w4 = pivots[pivots["movement_label"] == "W4"].iloc[-1]
        w3 = pivots[pivots["movement_label"] == "W3"].iloc[-1]
        w2 = pivots[pivots["movement_label"] == "W2"].iloc[-1]
        w1 = pivots[pivots["movement_label"] == "W1"].iloc[-1]

        # Rule §3.1: harga lower-low (W5 lebih rendah dari W3)
        if not (w5["price"] < w3["price"]):
            return None

        # Rule §2: minimal satu indikator higher-low (W5 vs W3)
        indicator_used = _find_confirming_indicator(indicators, int(w3["index"]), int(w5["index"]))
        if indicator_used is None:
            return None

        # Rule §3.3 poin 1 & 3: candle konfirmasi hijau berbadan, bukan doji,
        # dan window `df` yang dioper sudah dipotong sampai candle CLOSE saja
        # oleh caller (app/engine/backtest.py) -- lihat §8c.2.
        if not check_bullish_candle(df):
            return None  # doji / candle belum konfirmasi -> WAJIB tunggu candle berikutnya

        entry_price = float(df["Close"].iloc[-1])
        sl_price = float(df["Low"].iloc[-1])  # §3.4: low candle konfirmasi (termasuk wick)

        # Rule §3.5: TP = fib retracement HIGH(W4) -> LOW(W5), target minimal 0.6
        tp_levels = calculate_fib_levels(start=w4["price"], end=w5["price"], levels=[0.5, 0.6, 0.7])
        tp_price = tp_levels[0.6]

        risk = entry_price - sl_price
        reward = tp_price - entry_price
        if risk <= 0:
            return None  # struktur tidak valid (SL harus di bawah entry)
        rr = reward / risk

        plot_data = {
            "pivots": {
                "W1": {"idx": int(w1["index"]), "price": float(w1["price"])},
                "W2": {"idx": int(w2["index"]), "price": float(w2["price"])},
                "W3": {"idx": int(w3["index"]), "price": float(w3["price"])},
                "W4": {"idx": int(w4["index"]), "price": float(w4["price"])},
                "W5": {"idx": int(w5["index"]), "price": float(w5["price"])},
            },
            "fib_levels": {str(k): v for k, v in tp_levels.items()},
            "indicator": indicator_used,
        }

        return SetupResult(
            status="READY",
            strategy_name=self.name,
            symbol=df.attrs.get("symbol", "UNKNOWN"),
            timeframe=df.attrs.get("timeframe", "UNKNOWN"),
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            risk_reward=rr,
            score=rr * 10,
            metadata=plot_data,
        )


class DoubleBullishDivergenceStrategy(BaseStrategy):
    """
    final.md §3.6: Double Bullish Divergence.

    Kondisi (SEMUA wajib):
    1. Sudah ada 3 low berurutan L3 > L2 > L1 turun terus (L1 = paling baru).
    2. Minimal satu indikator higher-low sepanjang L3 -> L2 -> L1 (§2).
    3. Bullish divergence PERTAMA (leg L3->L2) GAGAL capai TP minimal 0.5
       sebelum breakdown lagi ke L1 (kondisi wajib terbentuknya Double, §3.6).
    4. Candle konfirmasi kedua valid (sama syarat §3.3).

    SL = Fib level "2" (extension 2x) dari basis L1 -> puncak yang tak
    tersentuh (§3.6: "jika harga break melewati Fib 2, indikator akan patah").
    TP pendek = fib retracement 0.5-0.7 dari puncak tak tersentuh -> L1.
    TP jauh (conditional) = "hutang" target bullish div pertama, HANYA aktif
    kalau breakout melewati puncak sebelumnya (§3.6).

    CATATAN PEMBATASAN STRUKTURAL: karena strategi ini hanya melihat 3 low
    TERBARU (tail(3)), otomatis membatasi maksimal "Double" -- final.md §3.6
    tegas melarang Triple/Quadruple bullish divergence, jadi TIDAK ada logika
    di file ini yang mencari pola lebih dari 2x reversal berturut-turut.
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Double Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if "type" not in pivots.columns:
            return None

        lows = pivots[pivots["type"] == -1].tail(3)
        highs = pivots[pivots["type"] == 1]

        if len(lows) < 3 or highs.empty:
            return None

        l1, l2, l3 = lows.iloc[-1], lows.iloc[-2], lows.iloc[-3]

        # Rule §3.6: harga lower-low berturut-turut, L1 (terbaru) < L2 < L3
        if not (l1["price"] < l2["price"] < l3["price"]):
            return None

        # Rule §2: minimal satu indikator higher-low sepanjang L3 -> L2 -> L1
        indicator_used = None
        for name in INDICATOR_PRIORITY:
            series = indicators.get(name)
            if series is None or series.empty:
                continue
            i1, i2, i3 = int(l1["index"]), int(l2["index"]), int(l3["index"])
            if max(i1, i2, i3) >= len(series):
                continue
            if series.iloc[i1] > series.iloc[i2] > series.iloc[i3]:
                indicator_used = name
                break
        if indicator_used is None:
            return None

        # High di antara L3 dan L2 (puncak setelah bullish div pertama terbentuk)
        h_first = highs[(highs["index"] > l3["index"]) & (highs["index"] < l2["index"])]
        if h_first.empty:
            return None
        untouched_high = float(h_first.iloc[-1]["price"])

        # Puncak tertinggi yang SEMPAT tercapai di antara L2 dan L1 (dipakai
        # untuk membuktikan bullish div pertama GAGAL capai TP 0.5, §3.6)
        h_between = highs[(highs["index"] > l2["index"]) & (highs["index"] < l1["index"])]
        if h_between.empty:
            return None
        peak_reached = float(h_between["price"].max())

        # Rule §3.6: TP 0.5 dari bullish div pertama (leg untouched_high -> L2)
        tp05_first = calculate_fib_levels(start=untouched_high, end=float(l2["price"]), levels=[0.5])[0.5]
        if peak_reached >= tp05_first:
            return None  # bullish div pertama SUDAH capai target -> bukan Double, tapi setup baru terpisah

        if not check_bullish_candle(df):
            return None

        entry_price = float(df["Close"].iloc[-1])

        # Rule §3.6: "Fibonacci retracement dari LOW candle konfirmasi pertama
        # -> HIGH (harga tertinggi yang tidak sempat tercapai) ... SL = di Fib '2'".
        # L2 dipakai sebagai proksi "low candle konfirmasi pertama" (low yang
        # terbentuk dari bullish divergence pertama). Level 2.0 = extension ke
        # BAWAH L2 sejauh jarak L2->untouched_high, sesuai alasan §3.6: "kalau
        # harga break melewati Fib 2, indikator akan patah / struktur berubah".
        sl_price = calculate_fib_levels(start=float(l2["price"]), end=untouched_high, levels=[2.0])[2.0]

        # TP pendek: fib retracement 0.5-0.7 dari untouched_high -> L1 (§3.6)
        tp_short_levels = calculate_fib_levels(start=untouched_high, end=float(l1["price"]), levels=[0.5, 0.6, 0.7])
        tp_short = tp_short_levels[0.6]

        # TP jauh: "hutang" target bullish div pertama -- HANYA aktif kalau
        # breakout melewati untouched_high (dicek & dieksekusi di level engine
        # / monitoring posisi berjalan, bukan di titik entry ini).
        tp_far = tp05_first

        risk = entry_price - sl_price
        reward = tp_short - entry_price
        if risk <= 0:
            return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "L3": {"idx": int(l3["index"]), "price": float(l3["price"])},
                "L2": {"idx": int(l2["index"]), "price": float(l2["price"])},
                "L1": {"idx": int(l1["index"]), "price": float(l1["price"])},
                "untouched_high": untouched_high,
                "peak_reached": peak_reached,
            },
            "fib_levels": {str(k): v for k, v in tp_short_levels.items()},
            "indicator": indicator_used,
            "is_double": True,
        }

        return SetupResult(
            status="READY",
            strategy_name=self.name,
            symbol=df.attrs.get("symbol", "UNKNOWN"),
            timeframe=df.attrs.get("timeframe", "UNKNOWN"),
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_short,
            tp_far=tp_far,
            risk_reward=rr,
            score=rr * 10,
            metadata=plot_data,
        )
