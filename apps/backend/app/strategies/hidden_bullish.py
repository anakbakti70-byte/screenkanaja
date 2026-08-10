import pandas as pd
from typing import Dict, Optional, Any
from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.fibonacci.extension import calculate_fib_extension
from app.confirmation.candle import check_bullish_candle

class HiddenBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Hidden Bullish Divergence (ABCDE)", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Hidden Bullish Divergence according to final.md §5.
        """
        if len(pivots) < 5: return None

        lows = pivots[pivots['type'] == -1].tail(2)
        highs = pivots[pivots['type'] == 1].tail(2)
        if len(lows) < 2 or len(highs) < 2: return None

        # A, C (Lows) | B, D (Highs)
        pA, pC = lows.iloc[-2], lows.iloc[-1]
        pB, pD = highs.iloc[-2], highs.iloc[-1]

        # Rule §5.1: Price Higher Low (C > A)
        if not (pC['price'] > pA['price']): return None

        # Rule §5.1: Indicator Lower Low (between C and A)
        div_found = False
        indicator_used = ""
        for name in ['AO', 'MACD', 'RSI']:
            series = indicators.get(name)
            if series is None or series.empty: continue
            if series.iloc[int(pC['index'])] < series.iloc[int(pA['index'])]:
                div_found = True
                indicator_used = name
                break
        if not div_found: return None

        # Rule §5.2: Zona Titik E (Fib 0.6 / 0.7 from Low C -> High D)
        zone_e = calculate_fib_levels(pC['price'], pD['price'], [0.6, 0.7])
        current_price = df['Close'].iloc[-1]

        in_zone = zone_e[0.7] <= current_price <= zone_e[0.6]
        if not in_zone: return None

        is_ready = check_bullish_candle(df)
        status = "READY" if is_ready else "WAIT_CONFIRMATION"

        # Rule §5.4: Take Profit (Fib 1.2 from point A)
        # Using wave A-D for projection
        tp_levels = calculate_fib_levels(pA['price'], pD['price'], [1.2])
        tp_price = tp_levels.get(1.2)

        # Rule §5.3: SL = LOW A
        sl_price = pA['price']

        risk = abs(current_price - sl_price)
        reward = abs(tp_price - current_price)
        rr = reward / risk if risk > 0 else 0

        plot_data = {
            "pivots": {
                "A": {"idx": int(pA['index']), "price": float(pA['price'])},
                "B": {"idx": int(pB['index']), "price": float(pB['price'])},
                "C": {"idx": int(pC['index']), "price": float(pC['price'])},
                "D": {"idx": int(pD['index']), "price": float(pD['price'])}
            },
            "fib_levels": { "zone_e": zone_e, "tp_12": tp_price },
            "indicator": indicator_used
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
            metadata={**plot_data, "indicator_used": indicator_used}
        )
