import pandas as pd

def check_bullish_candle(df: pd.DataFrame, body_threshold: float = 0.5) -> bool:
    """
    Checks if the last candle is bullish and its body is at least body_threshold of its total range.
    """
    if df.empty:
        return False
    
    last_candle = df.iloc[-1]
    open_price = last_candle['Open']
    close_price = last_candle['Close']
    high_price = last_candle['High']
    low_price = last_candle['Low']
    
    # Check if bullish
    if close_price <= open_price:
        return False
    
    body = close_price - open_price
    total_range = high_price - low_price
    
    if total_range == 0:
        return False
    
    return (body / total_range) >= body_threshold
