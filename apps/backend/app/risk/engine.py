import pandas as pd
from typing import Dict, Optional, Tuple

def calculate_risk_parameters(
    current_price: float,
    pivots: pd.DataFrame,
    entry_type: str = "long"
) -> Dict[str, Optional[float]]:
    """
    Calculates entry, SL, and TP based on pivots.
    For long:
    - SL: Recent Swing Low
    - TP: Fibonacci extension or fixed R:R
    """
    if pivots.empty or len(pivots) < 2:
        return {
            "entry": current_price,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None
        }

    # Get recent pivots
    # type -1 is Low, 1 is High
    lows = pivots[pivots['type'] == -1]
    highs = pivots[pivots['type'] == 1]

    if entry_type == "long":
        if lows.empty:
            return {"entry": current_price, "stop_loss": None, "take_profit": None, "risk_reward": None}
        
        # Stop loss at the last swing low
        stop_loss = lows.iloc[-1]['price']
        
        # Risk amount
        risk = current_price - stop_loss
        if risk <= 0:
            # If current price is below swing low, move SL further or invalidate
            stop_loss = current_price * 0.98 # 2% default
            risk = current_price - stop_loss

        # Take profit at 2:1 R:R or previous high
        take_profit = current_price + (risk * 2)
        if not highs.empty:
            last_high = highs.iloc[-1]['price']
            if last_high > current_price:
                 # Use previous high if it gives better R:R than 1.5
                 if (last_high - current_price) / risk >= 1.5:
                     take_profit = last_high

    else: # short
        if highs.empty:
            return {"entry": current_price, "stop_loss": None, "take_profit": None, "risk_reward": None}
        
        stop_loss = highs.iloc[-1]['price']
        risk = stop_loss - current_price
        if risk <= 0:
            stop_loss = current_price * 1.02
            risk = stop_loss - current_price
            
        take_profit = current_price - (risk * 2)
        if not lows.empty:
            last_low = lows.iloc[-1]['price']
            if last_low < current_price:
                if (current_price - last_low) / risk >= 1.5:
                    take_profit = last_low

    rr = calculate_rr(current_price, stop_loss, take_profit, entry_type)

    return {
        "entry": current_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_reward": rr
    }

def calculate_rr(entry: float, sl: float, tp: float, entry_type: str = "long") -> float:
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk == 0:
        return 0.0
    return round(reward / risk, 2)
