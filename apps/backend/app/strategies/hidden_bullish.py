import pandas as pd
from typing import Dict, Optional

from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.fibonacci.extension import calculate_fib_extension
from app.confirmation.candle import check_bullish_candle

INDICATOR_PRIORITY = ["AO", "MACD", "RSI"]


class HiddenBullishDivergenceStrategy(BaseStrategy):
    """
    final.md §5: Hidden Bullish Divergence (ABCDE) -- dipakai pada fase
    uptrend/continuation, BUKAN reversal.

    Syarat WAJIB (§5.1-§5.3), SEMUA harus terpenuhi:
    1. Pola konsolidasi A(low)-B(high)-C(low)-D(high) sudah terbentuk
       (min. 5 gerakan A-B-C-D-E, E adalah zona entry, bukan pivot final).
    2. Harga higher-low: C > A (§5.1).
    3. Indikator LEBIH RENDAH (kebalikan dari regular divergence, §5.1):
       minimal satu dari RSI/MACD/AO lower-low di C dibanding A.
    4. Harga masuk zona E = fib retracement 0.6/0.7 dari leg C->D (§5.2).
    5. Candle konfirmasi valid (§3.3).

    SL = LOW A (BUKAN low C, bukan low E -- §5.3, titik invalidasi tetap di low A).
    TP = fib extension dari leg (A->D) diproyeksikan dari titik A sendiri,
    level 1.0 (=D, level breakout) s.d. 1.2 (target minimal, §5.4).
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Hidden Bullish Divergence (ABCDE)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        if pivots.empty or "abcde_label" not in pivots.columns:
            return None

        rows_d = pivots[pivots["abcde_label"] == "D"]
        if rows_d.empty:
            return None

        pD = rows_d.iloc[-1]
        pC = pivots[pivots["abcde_label"] == "C"].iloc[-1]
        pB = pivots[pivots["abcde_label"] == "B"].iloc[-1]
        pA = pivots[pivots["abcde_label"] == "A"].iloc[-1]

        # Rule §5.1: harga higher-low (C > A) -- sudah divalidasi juga di
        # MovementClassifier.label_abcde, dicek ulang di sini supaya modul
        # strategi tidak diam-diam bergantung pada asumsi di modul lain.
        if not (pC["price"] > pA["price"]):
            return None

        # Rule §5.1: indikator LEBIH RENDAH di C dibanding A (kebalikan dari
        # regular divergence -- harga naik, indikator turun).
        indicator_used = None
        for name in INDICATOR_PRIORITY:
            series = indicators.get(name)
            if series is None or series.empty:
                continue
            idx_a, idx_c = int(pA["index"]), int(pC["index"])
            if max(idx_a, idx_c) >= len(series):
                continue
            if series.iloc[idx_c] < series.iloc[idx_a]:
                indicator_used = name
                break
        if indicator_used is None:
            return None

        # Rule §5.2: zona titik E = fib retracement 0.6/0.7 dari LOW C -> HIGH D
        zone_e = calculate_fib_levels(start=float(pC["price"]), end=float(pD["price"]), levels=[0.6, 0.7])
        current_price = float(df["Close"].iloc[-1])
        zone_high, zone_low = zone_e[0.6], zone_e[0.7]
        if not (zone_low <= current_price <= zone_high):
            return None

        if not check_bullish_candle(df):
            return None

        entry_price = current_price
        sl_price = float(pA["price"])  # Rule §5.3: SL selalu di low A

        # Rule §5.4: TP = fib extension leg (A->D), diproyeksikan dari A sendiri.
        # Level 1.0 jatuh tepat di D (level breakout), target minimal di 1.2.
        tp_levels = calculate_fib_extension(point_a=float(pA["price"]), point_b=float(pD["price"]),
                                             point_c=float(pA["price"]), levels=[1.0, 1.2])
        tp_price = tp_levels[1.2]
        breakout_level = tp_levels[1.0]

        risk = entry_price - sl_price
        reward = tp_price - entry_price
        if risk <= 0:
            return None
        rr = reward / risk

        plot_data = {
            "pivots": {
                "A": {"idx": int(pA["index"]), "price": float(pA["price"])},
                "B": {"idx": int(pB["index"]), "price": float(pB["price"])},
                "C": {"idx": int(pC["index"]), "price": float(pC["price"])},
                "D": {"idx": int(pD["index"]), "price": float(pD["price"])},
            },
            "fib_levels": {"zone_e": {str(k): v for k, v in zone_e.items()},
                            "breakout_level_1_0": breakout_level,
                            "tp_1_2": tp_price},
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
