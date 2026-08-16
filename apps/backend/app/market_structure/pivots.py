"""
Deteksi swing high/low (pivot) dengan metode ATR-ZigZag.

Catatan posisi dalam pipeline (final.md §9): "Elliott Wave hanya dipakai
sebagai penamaan/plotting posisi (1-2-3-4-5 / A-B-C / A-B-C-D-E), BUKAN basis
keputusan entry -- basis keputusan entry tetap selalu kembali ke divergence +
candle konfirmasi + level Fibonacci." Modul ini (dan movements.py) hanya
menyediakan KERANGKA/plotting wave; keputusan entry tetap ada di
app/strategies/*.py.
"""

import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import Dict, Optional

from app.indicators.ta import calculate_atr


def load_pivot_config(config_path: Optional[str] = None) -> Dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "pivot_thresholds.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)["pivot_detection"]


class PivotDetector:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_pivot_config()
        self.method = self.config.get("method", "atr_zigzag")
        self.atr_period = self.config.get("atr_period", 14)
        self.atr_multiplier = self.config.get("atr_multiplier", 1.5)
        self.min_bars = self.config.get("min_bars_between_pivots", 3)

    def detect_pivots(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mendeteksi pivot dengan ATR-ZigZag.

        Returns:
            DataFrame kolom ['index', 'price', 'type'] -- type: 1 = Swing High,
            -1 = Swing Low. `index` adalah posisi integer (iloc) di `df`, BUKAN
            label/timestamp, supaya gampang dipakai untuk slicing indikator
            (lihat app/strategies/bullish_divergence.py).
        """
        if df.empty or len(df) < self.atr_period:
            return pd.DataFrame(columns=["index", "price", "type"])

        atr = calculate_atr(df, length=self.atr_period)

        pivots = []
        trend = 0  # 0 = belum ditentukan, 1 = naik, -1 = turun
        last_pivot_val = float(df["Close"].iloc[0])
        last_pivot_idx = 0

        for i in range(1, len(df)):
            price_high = float(df["High"].iloc[i])
            price_low = float(df["Low"].iloc[i])
            current_atr = atr.iloc[i]

            if pd.isna(current_atr) or current_atr <= 0:
                continue

            threshold = current_atr * self.atr_multiplier

            if trend == 0:
                if price_high > last_pivot_val + threshold:
                    trend = 1
                    last_pivot_val = price_high
                    last_pivot_idx = i
                elif price_low < last_pivot_val - threshold:
                    trend = -1
                    last_pivot_val = price_low
                    last_pivot_idx = i

            elif trend == 1:
                if price_high > last_pivot_val:
                    last_pivot_val = price_high
                    last_pivot_idx = i
                elif price_low < last_pivot_val - threshold and (i - last_pivot_idx) >= self.min_bars:
                    pivots.append({"index": last_pivot_idx, "price": last_pivot_val, "type": 1})
                    trend = -1
                    last_pivot_val = price_low
                    last_pivot_idx = i

            elif trend == -1:
                if price_low < last_pivot_val:
                    last_pivot_val = price_low
                    last_pivot_idx = i
                elif price_high > last_pivot_val + threshold and (i - last_pivot_idx) >= self.min_bars:
                    pivots.append({"index": last_pivot_idx, "price": last_pivot_val, "type": -1})
                    trend = 1
                    last_pivot_val = price_high
                    last_pivot_idx = i

        # Pivot terakhir yang masih "berjalan" (belum dikonfirmasi reversal
        # berikutnya) TETAP disertakan -- ini penting karena W5/titik E pada
        # strategi selalu berupa pivot paling baru yang masih terbentuk.
        if trend != 0:
            pivots.append({"index": last_pivot_idx, "price": last_pivot_val, "type": trend})

        return pd.DataFrame(pivots, columns=["index", "price", "type"])
