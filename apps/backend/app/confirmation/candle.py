import pandas as pd

def check_bullish_candle(df: pd.DataFrame) -> bool:
    """
    Checks if the last candle is bullish and meets "cendol" criteria from final.md:
    1. Green (Close > Open)
    2. Has body (not a doji)
    """
    if df.empty:
        return False
    
    last_candle = df.iloc[-1]
    open_p = last_candle['Open']
    close_p = last_candle['Close']
    high_p = last_candle['High']
    low_p = last_candle['Low']
    
    # 1. Must be Green
    if close_p <= open_p:
        return False
    
    # 2. Must have body (Not a Doji)
    # Standard Doji definition: body <= 10% of total range
    body = close_p - open_p
    total_range = high_p - low_p
    
    if total_range == 0:
        return False

    is_doji = body <= (total_range * 0.1)

    return not is_doji
