import os
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from typing import List, Dict, Optional

def load_movement_config(config_path: Optional[str] = None) -> Dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "pivot_thresholds.yaml"
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)["movement_analysis"]

class MovementClassifier:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or load_movement_config()
        self.major_percentile = self.config.get("major_percentile", 70)
        self.lookback_window = self.config.get("lookback_window", 100)

    def classify_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """
        Classifies movements between pivots as Major or Minor.
        """
        if len(pivots_df) < 2:
            return pivots_df.copy().assign(magnitude=0, type="minor")

        pivots = pivots_df.copy()
        pivots['magnitude'] = pivots['price'].diff().abs()
        
        threshold = np.nanpercentile(pivots['magnitude'], self.major_percentile)
        pivots['movement_type'] = np.where(pivots['magnitude'] >= threshold, "major", "minor")
        
        return pivots

    def label_5_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """
        Labels movements 1 to 5 around the longest drop (Movement 3).
        Expects pivots_df with 'price' and 'type' (-1 for low, 1 for high).
        """
        if len(pivots_df) < 5:
            return pivots_df.copy().assign(movement_label=None)

        # Calculate drops (High to Low)
        pivots = pivots_df.copy()
        movements = []
        for i in range(1, len(pivots)):
            start = pivots.iloc[i-1]
            end = pivots.iloc[i]
            # Movement is a drop if it goes from High to Low
            magnitude = start['price'] - end['price'] if start['type'] == 1 and end['type'] == -1 else 0
            movements.append(magnitude)
        
        # Find the longest drop (candidate for Movement 3)
        if not any(m > 0 for m in movements):
            return pivots.assign(movement_label=None)
            
        m3_idx = np.argmax(movements) + 1 # +1 because movements are between i-1 and i
        
        # We need 2 movements before and 2 after
        # Structure: 1 (Up), 2 (Down), 3 (Down - Longest), 4 (Up), 5 (Down)
        # Wait, the rule says "bangun 5 gerakan (movement 1-5) di sekitarnya".
        # Typically in a bearish trend: 1: Drop, 2: Correction Up, 3: Longest Drop, 4: Correction Up, 5: Final Drop
        
        labels = [None] * len(pivots)
        
        # Assuming M3 is the longest drop (start at m3_idx-1, end at m3_idx)
        # We need pivots at m3_idx-3, m3_idx-2, m3_idx-1, m3_idx, m3_idx+1, m3_idx+2
        # But labeling is usually for segments. Let's label the end pivot of each movement.
        
        if m3_idx >= 2 and m3_idx + 2 < len(pivots):
            labels[m3_idx - 2] = 1
            labels[m3_idx - 1] = 2
            labels[m3_idx] = 3
            labels[m3_idx + 1] = 4
            labels[m3_idx + 2] = 5
            
        pivots['movement_label'] = labels
        return pivots
