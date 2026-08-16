import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any
from app.strategies.base import BaseStrategy, SetupResult
from app.confirmation.candle import check_bullish_candle

# ==============================================================================
# RINGKASAN PERBAIKAN (audit terhadap rulebook CTG §3-§8c)
# ------------------------------------------------------------------------------
# Semua bug di bawah ini adalah bug ARAH rumus Fibonacci: fungsi
# calculate_fib_levels(start, end, level) mendefinisikan level=0 -> start dan
# level=1 -> end. Konsekuensinya, "level lebih besar" HARUS berarti "titik
# lebih jauh dari start". Rulebook secara eksplisit mensyaratkan (§3.5, §3.6):
#   "Boleh TP parsial di level 0.5-0.6, SISANYA di 0.7"
# yang hanya masuk akal kalau TP(0.7) > TP(0.6) > TP(0.5) (jaraknya makin jauh
# dari entry). Untuk itu, level 0 HARUS diletakkan di titik dekat-entry (LOW),
# dan level 1 di titik target-jauh (HIGH) -- bukan sebaliknya.
#
# 1. BullishDivergenceStrategy.tp_levels
#    -> start/end tertukar (dulu start=W4/high, end=W5/low) sehingga TP(0.7)
#       < TP(0.6) < TP(0.5): makin besar levelnya, target malah makin DEKAT.
#       FIX: start=W5(low), end=W4(high)   [rulebook §3.5]
#
# 2. DoubleBullishDivergenceStrategy.sl_price (Fib "2")
#    -> start/end tertukar sehingga level "2" mengekstensi ke ATAS
#       untouched_high (SL di atas harga -- mustahil untuk posisi long).
#       FIX: start=untouched_high, end=L2(low)  [rulebook §3.6, skala 1-2-4-6
#       adalah ekstensi ke BAWAH low, konsisten dengan §3.2]
#
# 3. DoubleBullishDivergenceStrategy.tp05_first & tp_short_levels
#    -> start/end tertukar dengan bug yang sama seperti (1).
#       FIX: start=low, end=untouched_high   [rulebook §3.6, "sama seperti §3.5"]
#
# 4. CorrectionStrategy.wait_zone (zona tunggu Fib 0.6/0.7)
#    -> zone_high/zone_low DIBALIK penugasannya (zone_high diisi nilai level
#       0.6, zone_low diisi nilai level 0.7), padahal level 0.7 > level 0.6
#       (karena arah start=LOW->end=HIGH sudah benar di sini). Akibatnya
#       zone_low > zone_high dan syarat "zone_low <= price <= zone_high"
#       TIDAK PERNAH terpenuhi -- strategi Correction jadi mati total.
#       FIX: zone_low=level 0.6, zone_high=level 0.7   [rulebook §4.2]
#
# 5. CorrectionStrategy.breakout_min (syarat breakout minimal Fib 1.2)
#    -> point_c salah pakai tp_high (menghasilkan angka jauh di atas TP itu
#       sendiri, tidak masuk akal sebagai "syarat breakout MINIMAL").
#       FIX: point_c=bulldiv_low (sama seperti anchor pada point_a), sehingga
#       level 1.0 = tp_high persis dan level 1.2 = 20% di atas tp_high.
#       Ini konsisten dengan pola yang SUDAH BENAR di
#       HiddenBullishDivergenceStrategy (breakout_level, lihat §5.4).
#
# 6. HiddenBullishDivergenceStrategy.zone_e (zona E, Fib 0.6/0.7)
#    -> bug yang sama seperti (4): zone_high/zone_low dibalik.
#       FIX: zone_low=level 0.6, zone_high=level 0.7   [rulebook §5.2]
#
# 7. calculate_fib_extension: default argument mutable list diganti None+init
#    (code-quality, tidak mengubah hasil kalkulasi).
#
# Yang SUDAH BENAR dan TIDAK diubah (diverifikasi cocok dengan rulebook):
#   - Urutan prioritas indikator AO -> MACD -> RSI (§2)
#   - Definisi divergence W3 vs W5 pada BullishDivergenceStrategy (§2, §3.1)
#   - SL = low candle konfirmasi pada BullishDivergenceStrategy (§3.4)
#   - SL = LOW A & TP ekstensi 1.0/1.2 pada HiddenBullishDivergenceStrategy (§5.3-5.4)
#   - TP ekstensi 1.618 pada CorrectionStrategy, diproyeksikan dari correction_low (§4.4)
#
# CATATAN JUJUR (tidak bisa 100% dipastikan tanpa melihat struktur `pivots`
# yang sebenarnya): confluence_indicator pada CorrectionStrategy membandingkan
# titik HIGH (tp_high) dengan titik LOW (correction_low) menggunakan fungsi
# yang aslinya dirancang untuk membandingkan dua titik LOW (lihat §4.3 varian
# B: "muncul bullish divergence lagi di zona koreksi" idealnya butuh 2 pivot
# low di zona koreksi, bukan 1 high + 1 low). Data pivot low kedua di zona
# koreksi tidak tersedia di scope fungsi ini, jadi logika lama dipertahankan
# apa adanya (bukan bug yang bisa saya perbaiki dengan aman tanpa data
# tambahan) -- ditandai TODO di bawah.
# ==============================================================================

# ==============================================================================
# PART 1: FIBONACCI CALCULATIONS (Previously retracement.py & extension.py)
# ==============================================================================

def calculate_fib_levels(start: float, end: float, levels: List[float]) -> Dict[float, float]:
    """Calculates Fibonacci levels between start and end price.
    level=0 -> start, level=1 -> end. Caller MUST put the near-entry point
    as `start` and the far/target point as `end` so that a larger level
    means a larger distance from entry (see rulebook note at top of file)."""
    diff = end - start
    return {level: start + (diff * level) for level in levels}

def calculate_fib_extension(point_a: float, point_b: float, point_c: float, levels: Optional[List[float]] = None) -> Dict[float, float]:
    """Standard 3-point Fibonacci Extension (A=Low, B=High, C=Retracement)."""
    if levels is None:
        levels = [0.618, 1.0, 1.618]
    diff = point_b - point_a
    return {level: point_c + (diff * level) for level in levels}

# ==============================================================================
# PART 2: BULLISH DIVERGENCE (Previously bullish_divergence.py)
# ==============================================================================

INDICATOR_PRIORITY = ["AO", "MACD", "RSI"]

def _find_confirming_indicator(indicators: Dict[str, pd.Series], idx_low: int, idx_high: int) -> Optional[str]:
    for name in INDICATOR_PRIORITY:
        series = indicators.get(name)
        if series is None or series.empty: continue
        if idx_low >= len(series) or idx_high >= len(series): continue
        if series.iloc[idx_high] > series.iloc[idx_low]: return name
    return None

class BullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if pivots.empty or "movement_label" not in pivots.columns: return None
        w5_rows = pivots[pivots["movement_label"] == "W5"]
        if w5_rows.empty: return None

        w5 = w5_rows.iloc[-1]
        w4 = pivots[pivots["movement_label"] == "W4"].iloc[-1]
        w3 = pivots[pivots["movement_label"] == "W3"].iloc[-1]
        w2 = pivots[pivots["movement_label"] == "W2"].iloc[-1]
        w1 = pivots[pivots["movement_label"] == "W1"].iloc[-1]

        if not (w5["price"] < w3["price"]): return None
        indicator_used = _find_confirming_indicator(indicators, int(w3["index"]), int(w5["index"]))
        if indicator_used is None: return None
        if not check_bullish_candle(df): return None

        entry_price = float(df["Close"].iloc[-1])
        sl_price = float(df["Low"].iloc[-1])
        # FIX (§3.5): start harus di W5 (low, dekat entry), end di W4 (high,
        # target jauh) supaya TP(0.7) > TP(0.6) > TP(0.5), sesuai "TP parsial
        # di 0.5-0.6, sisanya di 0.7".
        tp_levels = calculate_fib_levels(start=w5["price"], end=w4["price"], levels=[0.5, 0.6, 0.7])
        tp_price = tp_levels[0.6]  # target minimal, per §3.5

        risk = entry_price - sl_price
        reward = tp_price - entry_price
        if risk <= 0: return None
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
        return SetupResult(status="READY", strategy_name=self.name, symbol=df.attrs.get("symbol", "UNKNOWN"),
                           timeframe=df.attrs.get("timeframe", "UNKNOWN"), entry_price=entry_price,
                           stop_loss=sl_price, take_profit=tp_price, risk_reward=rr, score=rr * 10, metadata=plot_data)

class DoubleBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Double Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if "type" not in pivots.columns: return None
        lows = pivots[pivots["type"] == -1].tail(3)
        highs = pivots[pivots["type"] == 1]
        if len(lows) < 3 or highs.empty: return None
        l1, l2, l3 = lows.iloc[-1], lows.iloc[-2], lows.iloc[-3]

        if not (l1["price"] < l2["price"] < l3["price"]): return None
        indicator_used = None
        for name in INDICATOR_PRIORITY:
            series = indicators.get(name)
            if series is None or series.empty: continue
            i1, i2, i3 = int(l1["index"]), int(l2["index"]), int(l3["index"])
            if max(i1, i2, i3) >= len(series): continue
            if series.iloc[i1] > series.iloc[i2] > series.iloc[i3]:
                indicator_used = name
                break
        if indicator_used is None: return None

        h_first = highs[(highs["index"] > l3["index"]) & (highs["index"] < l2["index"])]
        if h_first.empty: return None
        untouched_high = float(h_first.iloc[-1]["price"])
        h_between = highs[(highs["index"] > l2["index"]) & (highs["index"] < l1["index"])]
        if h_between.empty: return None
        peak_reached = float(h_between["price"].max())

        # FIX (§3.6, "sama seperti §3.5"): start=low(L2), end=high(untouched_high)
        tp05_first = calculate_fib_levels(start=float(l2["price"]), end=untouched_high, levels=[0.5])[0.5]
        if peak_reached >= tp05_first: return None
        if not check_bullish_candle(df): return None

        entry_price = float(df["Close"].iloc[-1])
        # FIX (§3.6, SL di Fib "2"): skala lokal 1-2-4-6 adalah EKSTENSI KE
        # BAWAH low (konsisten dengan §3.2), jadi start harus di titik HIGH
        # (untouched_high) dan end di titik LOW (L2) -- bukan sebaliknya.
        # Dengan start=untouched_high,end=L2: level 2.0 = 2*L2 - untouched_high,
        # yaitu di BAWAH L2 sejauh satu kali range (bulan) -- invalidasi struktural.
        sl_price = calculate_fib_levels(start=untouched_high, end=float(l2["price"]), levels=[2.0])[2.0]
        # FIX (§3.6, TP Pendek "sama seperti §3.5"): start=low(L1), end=high(untouched_high)
        tp_short_levels = calculate_fib_levels(start=float(l1["price"]), end=untouched_high, levels=[0.5, 0.6, 0.7])
        tp_short = tp_short_levels[0.6]
        tp_far = tp05_first  # "hutang" dari target bullish div pertama; aktif hanya jika breakout (lihat metadata)

        risk = entry_price - sl_price
        reward = tp_short - entry_price
        if risk <= 0: return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "L3": {"idx": int(l3["index"]), "price": float(l3["price"])},
                "L2": {"idx": int(l2["index"]), "price": float(l2["price"])},
                "L1": {"idx": int(l1["index"]), "price": float(l1["price"])},
                "untouched_high": untouched_high, "peak_reached": peak_reached,
            },
            "fib_levels": {str(k): v for k, v in tp_short_levels.items()},
            "indicator": indicator_used, "is_double": True,
        }
        return SetupResult(status="READY", strategy_name=self.name, symbol=df.attrs.get("symbol", "UNKNOWN"),
                           timeframe=df.attrs.get("timeframe", "UNKNOWN"), entry_price=entry_price,
                           stop_loss=sl_price, take_profit=tp_short, tp_far=tp_far, risk_reward=rr,
                           score=rr * 10, metadata=plot_data)

# ==============================================================================
# PART 3: CORRECTION STRATEGY (Previously correction.py)
# ==============================================================================

class CorrectionStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Correction (ABC)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        lows = pivots[pivots["type"] == -1]
        highs = pivots[pivots["type"] == 1]
        if len(lows) < 2 or highs.empty: return None

        bulldiv_low = lows.iloc[-2]
        tp_high = highs.iloc[-1]
        correction_low = lows.iloc[-1]

        if not (tp_high["index"] > bulldiv_low["index"] and correction_low["index"] > tp_high["index"]): return None
        if not (tp_high["price"] > bulldiv_low["price"] and correction_low["price"] < tp_high["price"]): return None

        # start=LOW(bulldiv_low) -> end=HIGH(tp_high), arah ini sudah benar (§4.2),
        # jadi level 0.7 > level 0.6 secara nilai.
        wait_zone = calculate_fib_levels(start=bulldiv_low["price"], end=tp_high["price"], levels=[0.6, 0.7])
        current_price = float(df["Close"].iloc[-1])
        # FIX (§4.2): zone_low harus level 0.6 (lebih dekat ke bulldiv_low),
        # zone_high harus level 0.7 (lebih dekat ke tp_high). Sebelumnya
        # tertukar sehingga zone_low > zone_high dan strategi ini TIDAK PERNAH
        # bisa lolos filter zona tunggu.
        zone_low, zone_high = wait_zone[0.6], wait_zone[0.7]
        if not (zone_low <= current_price <= zone_high): return None
        if not check_bullish_candle(df): return None

        # TODO: idealnya varian B (§4.3) membandingkan dua pivot LOW di zona
        # koreksi (divergence baru di time frame kecil), bukan HIGH vs LOW.
        # Data pivot low kedua di zona koreksi tidak tersedia di scope ini,
        # jadi logika ini dipertahankan sebagai proxy momentum yang ada.
        confluence_indicator = _find_confirming_indicator(indicators, int(tp_high["index"]), int(correction_low["index"]))
        variant = "B_full_confluence" if confluence_indicator else "A_strict_invalidation"
        sl_price = float(correction_low["price"]) if confluence_indicator else float(bulldiv_low["price"])

        tp_ext = calculate_fib_extension(point_a=float(bulldiv_low["price"]), point_b=float(tp_high["price"]),
                                          point_c=float(correction_low["price"]), levels=[1.618])
        tp_price = tp_ext[1.618]
        # FIX (§4.4, "syarat breakout minimal Fib 1.2"): point_c harus sama
        # dengan point_a (bulldiv_low), bukan tp_high, supaya level 1.0 =
        # tp_high persis dan level 1.2 = 20% di atas tp_high (pola yang sama
        # dengan breakout_level pada HiddenBullishDivergenceStrategy §5.4).
        # Sebelumnya point_c=tp_high menghasilkan angka jauh melampaui
        # target TP itu sendiri -- tidak masuk akal sebagai syarat "minimal".
        breakout_min = calculate_fib_extension(point_a=float(bulldiv_low["price"]), point_b=float(tp_high["price"]),
                                                point_c=float(bulldiv_low["price"]), levels=[1.2])[1.2]

        risk = current_price - sl_price
        reward = tp_price - current_price
        if risk <= 0: return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "bulldiv_low": {"idx": int(bulldiv_low["index"]), "price": float(bulldiv_low["price"])},
                "tp_high": {"idx": int(tp_high["index"]), "price": float(tp_high["price"])},
                "correction_low": {"idx": int(correction_low["index"]), "price": float(correction_low["price"])},
            },
            "fib_levels": {"wait_zone": {str(k): v for k, v in wait_zone.items()},
                            "tp_extension_1618": tp_price, "breakout_min_fib_1_2": breakout_min},
            "variant": variant, "confluence_indicator": confluence_indicator,
        }
        return SetupResult(status="READY", strategy_name=self.name, symbol=df.attrs.get("symbol", "UNKNOWN"),
                           timeframe=df.attrs.get("timeframe", "UNKNOWN"), entry_price=current_price,
                           stop_loss=sl_price, take_profit=tp_price, risk_reward=rr, score=rr * 10, metadata=plot_data)

# ==============================================================================
# PART 4: HIDDEN BULLISH (Previously hidden_bullish.py)
# ==============================================================================

class HiddenBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Hidden Bullish Divergence (ABCDE)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if pivots.empty or "abcde_label" not in pivots.columns: return None
        rows_d = pivots[pivots["abcde_label"] == "D"]
        if rows_d.empty: return None

        pD = rows_d.iloc[-1]
        pC = pivots[pivots["abcde_label"] == "C"].iloc[-1]
        pB = pivots[pivots["abcde_label"] == "B"].iloc[-1]
        pA = pivots[pivots["abcde_label"] == "A"].iloc[-1]

        if not (pC["price"] > pA["price"]): return None
        indicator_used = None
        for name in INDICATOR_PRIORITY:
            series = indicators.get(name)
            if series is None or series.empty: continue
            idx_a, idx_c = int(pA["index"]), int(pC["index"])
            if max(idx_a, idx_c) >= len(series): continue
            if series.iloc[idx_c] < series.iloc[idx_a]:
                indicator_used = name
                break
        if indicator_used is None: return None

        # start=LOW(pC) -> end=HIGH(pD), arah ini sudah benar (§5.2).
        zone_e = calculate_fib_levels(start=float(pC["price"]), end=float(pD["price"]), levels=[0.6, 0.7])
        current_price = float(df["Close"].iloc[-1])
        # FIX (§5.2): zone_low = level 0.6 (dekat pC), zone_high = level 0.7
        # (dekat pD). Sebelumnya tertukar sehingga zone_low > zone_high dan
        # filter zona E tidak pernah lolos.
        zone_low, zone_high = zone_e[0.6], zone_e[0.7]
        if not (zone_low <= current_price <= zone_high): return None
        if not check_bullish_candle(df): return None

        entry_price, sl_price = current_price, float(pA["price"])
        tp_levels = calculate_fib_extension(point_a=float(pA["price"]), point_b=float(pD["price"]),
                                             point_c=float(pA["price"]), levels=[1.0, 1.2])
        tp_price, breakout_level = tp_levels[1.2], tp_levels[1.0]

        risk, reward = entry_price - sl_price, tp_price - entry_price
        if risk <= 0: return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "A": {"idx": int(pA["index"]), "price": float(pA["price"])},
                "B": {"idx": int(pB["index"]), "price": float(pB["price"])},
                "C": {"idx": int(pC["index"]), "price": float(pC["price"])},
                "D": {"idx": int(pD["index"]), "price": float(pD["price"])},
            },
            "fib_levels": {"zone_e": {str(k): v for k, v in zone_e.items()}, "breakout_level_1_0": breakout_level, "tp_1_2": tp_price},
            "indicator": indicator_used,
        }
        return SetupResult(status="READY", strategy_name=self.name, symbol=df.attrs.get("symbol", "UNKNOWN"),
                           timeframe=df.attrs.get("timeframe", "UNKNOWN"), entry_price=entry_price,
                           stop_loss=sl_price, take_profit=tp_price, risk_reward=rr, score=rr * 10, metadata=plot_data)