import pandas as pd
from typing import Dict, Optional, Any
from app.strategies.base import BaseStrategy, SetupResult

class HiddenBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Hidden Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Hidden Bullish Divergence logic.
        1. Trend = uptrend
        2. Price: Higher Low
        3. Indicator: Lower Low
        """
        if len(pivots) < 2:
            return None

        # Get the last two Swing Lows
        lows = pivots[pivots['type'] == -1].tail(2)
        if len(lows) < 2:
            return None

        last_low = lows.iloc[-1]
        prev_low = lows.iloc[-2]

        # Price: Higher Low (Uptrend continuation)
        if not (last_low['price'] > prev_low['price']):
            return None

        # Indicators: Lower Low
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
            
            if val_last < val_prev:
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
            stop_loss=last_low['price'],
            metadata={
                "indicators": matching_indicators,
                "prev_low_price": prev_low['price'],
                "last_low_price": last_low['price']
            }
        )
