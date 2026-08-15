import pandas as pd
import numpy as np

def calculate_ao(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> pd.Series:
    """
    Awesome Oscillator (AO) - Bill Williams Official Formula
    Median Price = (High + Low) / 2
    AO = SMA(Median Price, 5) - SMA(Median Price, 34)
    """
    if df.empty or 'High' not in df.columns or 'Low' not in df.columns:
        return pd.Series(dtype='float64')

    # 1. Hitung Median Price
    median_price = (df['High'] + df['Low']) / 2

    # 2. Hitung SMA 5 dan SMA 34 dari Median Price
    sma5 = median_price.rolling(window=fast).mean()
    sma34 = median_price.rolling(window=slow).mean()

    # 3. AO adalah selisihnya
    ao = sma5 - sma34
    return ao

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    if df.empty or 'Close' not in df.columns:
        return pd.Series(dtype='float64')
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/length, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/length, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    if df.empty or 'Close' not in df.columns:
        return pd.DataFrame()
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    sig = macd.ewm(span=signal, adjust=False).mean()
    hist = macd - sig
    return pd.DataFrame({'macd': macd, 'signal': sig, 'hist': hist})

def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Average True Range (ATR)
    """
    if df.empty or 'High' not in df.columns or 'Low' not in df.columns or 'Close' not in df.columns:
        return pd.Series(dtype='float64')

    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)

    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low - close_prev).abs()
    ], axis=1).max(axis=1)

    return tr.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
