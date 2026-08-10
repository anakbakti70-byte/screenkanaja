import pandas as pd
import numpy as np

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI) - Manual Implementation (Wilder's Smoothing)
    """
    if df.empty or 'Close' not in df.columns:
        return pd.Series()

    delta = df['Close'].diff()
    gain = delta.copy()
    loss = delta.copy()
    gain[gain < 0] = 0
    loss[loss > 0] = 0

    # Wilder's Smoothing
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.abs().ewm(alpha=1/length, min_periods=length, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence (MACD) - Manual Implementation
    """
    if df.empty or 'Close' not in df.columns:
        return pd.DataFrame()

    close = df['Close']
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        f'MACD_{fast}_{slow}_{signal}': macd_line,
        f'MACDh_{fast}_{slow}_{signal}': histogram,
        f'MACDs_{fast}_{slow}_{signal}': signal_line
    })

def calculate_ao(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> pd.Series:
    """
    Awesome Oscillator (AO) - Manual Implementation
    """
    if df.empty or 'High' not in df.columns or 'Low' not in df.columns:
        return pd.Series()

    median_price = (df['High'] + df['Low']) / 2
    ao_series = median_price.rolling(window=fast).mean() - median_price.rolling(window=slow).mean()
    return ao_series

def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Average True Range (ATR) - Manual Implementation
    """
    if df.empty or 'High' not in df.columns or 'Low' not in df.columns or 'Close' not in df.columns:
        return pd.Series()

    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)

    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low - close_prev).abs()
    ], axis=1).max(axis=1)

    # Wilder's Smoothing for ATR
    return tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
