import os
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from app.indicators.ta import calculate_atr

def load_pivot_config(config_path: Optional[str] = None) -> Dict:
    if config_path is None:
        # Path relative to this file: ../config/pivot_thresholds.yaml
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
        Detects pivots using ATR-based ZigZag.
        Returns a DataFrame with columns: ['index', 'price', 'type'] (type: 1 for High, -1 for Low)
        """
        if df.empty or len(df) < self.atr_period:
            return pd.DataFrame(columns=['index', 'price', 'type'])

        atr = calculate_atr(df, length=self.atr_period)
        
        pivots = []
        # Initial direction (arbitrary, will be corrected)
        trend = 0 # 1 for up, -1 for down
        last_pivot_val = df['Close'].iloc[0]
        last_pivot_idx = 0
        
        for i in range(1, len(df)):
            price_high = df['High'].iloc[i]
            price_low = df['Low'].iloc[i]
            current_atr = atr.iloc[i]
            
            if pd.isna(current_atr):
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
                # Looking for a new high or a reversal
                if price_high > last_pivot_val:
                    last_pivot_val = price_high
                    last_pivot_idx = i
                elif price_low < last_pivot_val - threshold and (i - last_pivot_idx) >= self.min_bars:
                    # Confirm Swing High
                    pivots.append({'index': last_pivot_idx, 'price': last_pivot_val, 'type': 1})
                    trend = -1
                    last_pivot_val = price_low
                    last_pivot_idx = i
            elif trend == -1:
                # Looking for a new low or a reversal
                if price_low < last_pivot_val:
                    last_pivot_val = price_low
                    last_pivot_idx = i
                elif price_high > last_pivot_val + threshold and (i - last_pivot_idx) >= self.min_bars:
                    # Confirm Swing Low
                    pivots.append({'index': last_pivot_idx, 'price': last_pivot_val, 'type': -1})
                    trend = 1
                    last_pivot_val = price_high
                    last_pivot_idx = i

        # Add the last pending pivot if any
        if last_pivot_idx != 0:
            pivots.append({'index': last_pivot_idx, 'price': last_pivot_val, 'type': trend})

        return pd.DataFrame(pivots)
