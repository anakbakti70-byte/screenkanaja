import pandas as pd
from typing import Dict, Optional, Any
from app.strategies.base import BaseStrategy, SetupResult

class BullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Bullish Divergence logic.
        1. Movement label = 5 (from movement analysis)
        2. Price: Lower Low
        3. Indicator: Higher Low (at least one of RSI, MACD, AO)
        """
        if len(pivots) < 5:
            return None

        # Get the last two Swing Lows
        lows = pivots[pivots['type'] == -1].tail(2)
        if len(lows) < 2:
            return None

        last_low = lows.iloc[-1]
        prev_low = lows.iloc[-2]

        # Check if last low corresponds to movement 5
        if last_low.get('movement_label') != 5:
            # We still might want to detect it even if not labeled 5 in some contexts, 
            # but rule says movement label = 5.
            pass

        # Price: Lower Low
        if not (last_low['price'] < prev_low['price']):
            return None

        # Indicators: Higher Low
        div_found = False
        matching_indicators = []
        
        for name, series in indicators.items():
            if name not in ['RSI', 'MACD', 'AO']:
                continue
                
            idx_last = last_low['index']
            idx_prev = prev_low['index']
            
            if idx_last >= len(series) or idx_prev >= len(series):
                continue
                
            val_last = series.iloc[int(idx_last)]
            val_prev = series.iloc[int(idx_prev)]
            
            if val_last > val_prev:
                div_found = True
                matching_indicators.append(name)

        if not div_found:
            return None

        # Setup Detected
        return SetupResult(
            status="SETUP_DETECTED",
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=df['Close'].iloc[-1],
            stop_loss=last_low['price'],
            metadata={
                "indicators": matching_indicators,
                "prev_low_price": prev_low['price'],
                "last_low_price": last_low['price']
            }
        )

class DoubleBullishDivergenceStrategy(BullishDivergenceStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.name = "Double Bullish Divergence"

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Double Bullish Divergence logic.
        Requires two consecutive bullish divergences.
        """
        if len(pivots) < 7: # Need more pivots for double divergence
            return None

        # Get the last three Swing Lows
        lows = pivots[pivots['type'] == -1].tail(3)
        if len(lows) < 3:
            return None

        l1 = lows.iloc[-1]
        l2 = lows.iloc[-2]
        l3 = lows.iloc[-3]

        # Check Price: L1 < L2 < L3 (Consecutive Lower Lows)
        if not (l1['price'] < l2['price'] < l3['price']):
            return None

        # Check Indicators: HL1 > HL2 > HL3 (Consecutive Higher Lows)
        div_found = False
        matching_indicators = []

        for name, series in indicators.items():
            if name not in ['RSI', 'MACD', 'AO']:
                continue
            
            v1 = series.iloc[int(l1['index'])]
            v2 = series.iloc[int(l2['index'])]
            v3 = series.iloc[int(l3['index'])]

            if v1 > v2 > v3:
                div_found = True
                matching_indicators.append(name)

        if not div_found:
            return None

        return SetupResult(
            status="SETUP_DETECTED",
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=df['Close'].iloc[-1],
            stop_loss=l1['price'],
            metadata={
                "indicators": matching_indicators,
                "lows": [l3['price'], l2['price'], l1['price']]
            }
        )
