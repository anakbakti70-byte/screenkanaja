import pandas as pd
from typing import Dict, Optional, Any
from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.fibonacci.extension import calculate_fib_extension
from app.confirmation.candle import check_bullish_candle

class CorrectionStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Correction (ABC)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Correction (ABC) according to final.md §4.
        """
        if len(pivots) < 3: return None
        
        lows = pivots[pivots['type'] == -1]
        highs = pivots[pivots['type'] == 1]
        if len(lows) < 2 or len(highs) < 1: return None
            
        # A = Puncak setelah TP (High), B = Low koreksi saat ini, C = Titik Tunggu
        bullish_div_low = lows.iloc[-2]
        tp_high = highs.iloc[-1]
        
        # Rule §4.2: Zona Tunggu Koreksi (Fib 0.6 / 0.7) from Bullish Div Low -> TP High
        wait_zone = calculate_fib_levels(bullish_div_low['price'], tp_high['price'], [0.6, 0.7])
        current_price = df['Close'].iloc[-1]

        in_zone = wait_zone[0.7] <= current_price <= wait_zone[0.6]
        if not in_zone: return None

        is_ready = check_bullish_candle(df)
        status = "READY" if is_ready else "WAIT_CONFIRMATION"

        # Rule §4.4: TP Extension 1.618
        current_low = df['Low'].iloc[-1]
        tp_extension = calculate_fib_extension(bullish_div_low['price'], tp_high['price'], current_low, [1.618])
        tp_price = tp_extension.get(1.618)

        # Rule §4.3: SL = low bullish divergence SEBELUMNYA
        sl_price = bullish_div_low['price']

        risk = abs(current_price - sl_price)
        reward = abs(tp_price - current_price)
        rr = reward / risk if risk > 0 else 0

        plot_data = {
            "pivots": {
                "Low_A": {"idx": int(bullish_div_low['index']), "price": float(bullish_div_low['price'])},
                "High_B": {"idx": int(tp_high['index']), "price": float(tp_high['price'])}
            },
            "fib_levels": { "wait_zone": wait_zone, "tp_extension": tp_price }
        }

        return SetupResult(
            status=status,
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=float(current_price),
            stop_loss=float(sl_price),
            take_profit=float(tp_price),
            risk_reward=float(rr),
            score=float(rr * 10),
            metadata=plot_data
        )
