import pandas as pd
import numpy as np
from typing import Dict, Optional, Any, List
from app.strategies.base import BaseStrategy, SetupResult
from app.fibonacci.retracement import calculate_fib_levels
from app.confirmation.candle import check_bullish_candle

class BullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Bullish Divergence (Regular) according to final.md §3.
        Strictly requires 1-2-3-4-5 wave structure where Wave 3 is the longest drop.
        """
        if pivots.get('movement_label') is None: return None

        # Identify Wave 5 (Last low in the sequence)
        w5_pivots = pivots[pivots['movement_label'] == 'W5']
        if w5_pivots.empty: return None

        w5_low = w5_pivots.iloc[-1]
        w3_low = pivots[pivots['movement_label'] == 'W3'].iloc[-1]
        w4_high = pivots[pivots['movement_label'] == 'W4'].iloc[-1]
        w2_high = pivots[pivots['movement_label'] == 'W2'].iloc[-1]

        # Rule §3.1: Price Lower Low (W5 < W3)
        if not (w5_low['price'] < w3_low['price']):
            return None

        # Rule §2: Indicator Higher Low
        div_found = False
        indicator_used = ""
        for name in ['AO', 'MACD', 'RSI']:
            series = indicators.get(name)
            if series is None or series.empty: continue

            val_w5 = series.iloc[int(w5_low['index'])]
            val_w3 = series.iloc[int(w3_low['index'])]

            if val_w5 > val_w3:
                div_found = True
                indicator_used = name
                break

        if not div_found: return None

        # Rule §3.3: Candle Konfirmasi
        is_ready = check_bullish_candle(df)
        status = "READY" if is_ready else "WAIT_CONFIRMATION"

        # Fibonacci Wait Zone (§3.2): Low(W3) -> High(W2) -> 1.2/1.4/1.6
        wait_zones = calculate_fib_levels(w2_high['price'], w3_low['price'], [1.2, 1.4, 1.6])

        # TP Levels (§3.5): High(W4) -> Low(W5) -> 0.5/0.6/0.7
        tp_levels = calculate_fib_levels(w4_high['price'], w5_low['price'], [0.5, 0.6, 0.7])

        entry_price = float(df['Close'].iloc[-1])
        sl_price = float(df['Low'].iloc[-1]) # Low of confirmation candle
        tp_price = float(tp_levels.get(0.6))

        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr = reward / risk if risk > 0 else 0

        plot_data = {
            "pivots": {
                "W1": {"idx": int(pivots[pivots['movement_label'] == 'W1'].iloc[-1]['index']), "price": float(pivots[pivots['movement_label'] == 'W1'].iloc[-1]['price'])},
                "W2": {"idx": int(w2_high['index']), "price": float(w2_high['price'])},
                "W3": {"idx": int(w3_low['index']), "price": float(w3_low['price'])},
                "W4": {"idx": int(w4_high['index']), "price": float(w4_high['price'])},
                "W5": {"idx": int(w5_low['index']), "price": float(w5_low['price'])}
            },
            "fib_levels": { "wait_zone": wait_zones, "tp_zone": tp_levels },
            "indicator": indicator_used
        }

        return SetupResult(
            status=status,
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            risk_reward=rr,
            score=rr * 10,
            metadata=plot_data
        )

class DoubleBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Double Bullish Divergence", config)

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Implements Double Bullish Divergence according to final.md §3.6.
        Requires two consecutive bullish divergences where the first didn't reach TP 0.5.
        """
        lows = pivots[pivots['type'] == -1].tail(3)
        if len(lows) < 3: return None

        l1, l2, l3 = lows.iloc[-1], lows.iloc[-2], lows.iloc[-3]

        # Price: L1 < L2 < L3
        if not (l1['price'] < l2['price'] < l3['price']): return None

        # Indicator: HL1 > HL2 > HL3
        div_found = False
        indicator_used = ""
        for name in ['AO', 'MACD', 'RSI']:
            series = indicators.get(name)
            if series is None or series.empty: continue
            v1, v2, v3 = series.iloc[int(l1['index'])], series.iloc[int(l2['index'])], series.iloc[int(l3['index'])]
            if v1 > v2 > v3:
                div_found = True
                indicator_used = name
                break
        if not div_found: return None

        # Check if L2 Setup didn't reach TP 0.5
        highs = pivots[pivots['type'] == 1]
        high_between_l2_l1 = highs[(highs['index'] > l2['index']) & (highs['index'] < l1['index'])]
        if high_between_l2_l1.empty: return None

        peak_reached = high_between_l2_l1['price'].max()
        # TP 0.5 for L2 would have been from previous high to L2
        high_before_l2 = highs[highs['index'] < l2['index']]
        if high_before_l2.empty: return None
        h_prev = high_before_l2.iloc[-1]['price']
        tp05_l2 = h_prev - (h_prev - l2['price']) * 0.5

        if peak_reached >= tp05_l2: return None # It hit TP 0.5, not a "double" failure

        is_ready = check_bullish_candle(df)
        status = "READY" if is_ready else "WAIT_CONFIRMATION"

        # SL at Fib level "2" from L2 -> Peak -> 2.0
        fib_levels = calculate_fib_levels(peak_reached, l2['price'], [2.0, 0.6])
        sl_price = float(fib_levels.get(2.0))
        tp_short = float(fib_levels.get(0.6))

        entry_price = float(df['Close'].iloc[-1])
        risk = abs(entry_price - sl_price)
        reward = abs(tp_short - entry_price)
        rr = reward / risk if risk > 0 else 0

        plot_data = {
            "pivots": {
                "L3": {"idx": int(l3['index']), "price": float(l3['price'])},
                "L2": {"idx": int(l2['index']), "price": float(l2['price'])},
                "L1": {"idx": int(l1['index']), "price": float(l1['price'])}
            },
            "fib_levels": { "sl_fib2": sl_price, "tp_short": tp_short },
            "indicator": indicator_used
        }

        return SetupResult(
            status=status,
            strategy_name=self.name,
            symbol=df.attrs.get('symbol', 'UNKNOWN'),
            timeframe=df.attrs.get('timeframe', 'UNKNOWN'),
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_short,
            risk_reward=rr,
            score=rr * 10,
            metadata=plot_data
        )
