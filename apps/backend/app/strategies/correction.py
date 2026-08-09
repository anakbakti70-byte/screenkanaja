import pandas as pd
from typing import Dict, Optional, Any, List
from app.strategies.base import BaseStrategy, SetupResult

class CorrectionStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Correction", config)
        self.retracement_zones = self.config.get("fibonacci", {}).get("retracement_zones", [[0.382, 0.618]])

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Fibonacci-based Correction strategy.
        1. Identifies a recent strong move (Swing Low to Swing High).
        2. Checks if current price is in the Fibonacci retracement zone.
        """
        if len(pivots) < 2:
            return None

        # Look for the last High and the Low before it
        last_pivots = pivots.tail(3)
        if len(last_pivots) < 2:
            return None
            
        # We need a Low followed by a High
        high_idx = -1
        low_idx = -1
        
        for i in range(len(last_pivots)-1, 0, -1):
            if last_pivots.iloc[i]['type'] == 1: # High
                high_idx = i
                # Look for the Low before this High
                for j in range(i-1, -1, -1):
                    if last_pivots.iloc[j]['type'] == -1: # Low
                        low_idx = j
                        break
                if low_idx != -1:
                    break
        
        if high_idx == -1 or low_idx == -1:
            return None
            
        swing_low = last_pivots.iloc[low_idx]['price']
        swing_high = last_pivots.iloc[high_idx]['price']
        current_price = df['Close'].iloc[-1]
        
        if swing_high <= swing_low:
            return None
            
        diff = swing_high - swing_low
        
        # Check if price is in any of the retracement zones
        in_zone = False
        target_zone = None
        for zone in self.retracement_zones:
            lower_bound = swing_high - (zone[1] * diff)
            upper_bound = swing_high - (zone[0] * diff)
            
            if lower_bound <= current_price <= upper_bound:
                in_zone = True
                target_zone = zone
                break
        
        if not in_zone:
            return None

        # Calculate Extensions for TP
        extensions = self.config.get("fibonacci", {}).get("extension_targets", [1.0, 1.618])
        tp_levels = [swing_low + (ext * diff) for ext in extensions]

        return SetupResult(
            status="WAIT_CONFIRMATION",
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=current_price,
            stop_loss=swing_low,
            take_profit=tp_levels[0] if tp_levels else None,
            metadata={
                "retracement_zone": target_zone,
                "swing_low": swing_low,
                "swing_high": swing_high,
                "tp_levels": tp_levels
            }
        )
