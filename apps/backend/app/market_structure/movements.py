import os
import pandas as pd
import numpy as np
from typing import List, Dict, Optional

class MovementClassifier:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def classify_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        if len(pivots_df) < 2:
            return pivots_df.copy()
        pivots = pivots_df.copy()
        pivots['magnitude'] = pivots['price'].diff().abs()
        return pivots

    def label_5_movements(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        """
        Labels 1-2-3-4-5 structure according to final.md §3.1.
        Optimized to find more valid setups.
        """
        if len(pivots_df) < 5:
            return pivots_df.copy().assign(movement_label=None)

        pivots = pivots_df.copy()
        labels = [None] * len(pivots)

        # Sequence: Low-High-Low-High-Low (-1, 1, -1, 1, -1)
        # We search from the most recent pivots
        for i in range(len(pivots) - 1, 3, -1):
            p5 = pivots.iloc[i]   # Current Low (End of W5)
            p4 = pivots.iloc[i-1] # Previous High (End of W4)
            p3 = pivots.iloc[i-2] # Previous Low (End of W3)
            p2 = pivots.iloc[i-3] # Previous High (End of W2)
            p1 = pivots.iloc[i-4] # Start Low (End of W1)
            
            if (p5['type'] == -1 and p4['type'] == 1 and
                p3['type'] == -1 and p2['type'] == 1 and p1['type'] == -1):

                # Rule §3.1: Identify longest drop (Wave 3)
                drop1 = p2['price'] - p1['price'] # (Not used as much but part of structure)
                drop3 = p2['price'] - p3['price']
                drop5 = p4['price'] - p5['price']

                # In final.md, Wave 3 is "penurunan terpanjang"
                # If drop3 is the largest of the drops we have, it's a valid CTG structure
                if drop3 > drop5 and drop3 > 0:
                    labels[i] = "W5"
                    labels[i-1] = "W4"
                    labels[i-2] = "W3"
                    labels[i-3] = "W2"
                    labels[i-4] = "W1"
                    # Break only if we want the absolute latest, but for backtest
                    # this method is usually called bar-by-bar anyway.
                    break

        pivots['movement_label'] = labels
        return pivots

    def label_abcde(self, pivots_df: pd.DataFrame) -> pd.DataFrame:
        if len(pivots_df) < 5:
            return pivots_df.copy().assign(abcde_label=None)

        pivots = pivots_df.copy()
        labels = [None] * len(pivots)

        # Consolidation pattern check
        for i in range(len(pivots) - 1, 3, -1):
            subset = pivots.iloc[i-4:i+1]
            # Alternating types
            if (subset['type'].diff().abs() == 2).all():
                labels[i] = "E"
                labels[i-1] = "D"
                labels[i-2] = "C"
                labels[i-3] = "B"
                labels[i-4] = "A"
                break

        pivots['abcde_label'] = labels
        return pivots
