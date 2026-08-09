import pandas as pd
import pandas_ta as ta

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI)
    """
    if df.empty:
        return pd.Series()
    return ta.rsi(df['Close'], length=length)

def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence (MACD)
    Returns a DataFrame with MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    """
    if df.empty:
        return pd.DataFrame()
    return ta.macd(df['Close'], fast=fast, slow=slow, signal=signal)

def calculate_ao(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> pd.Series:
    """
    Awesome Oscillator (AO)
    """
    if df.empty:
        return pd.Series()
    return ta.ao(df['High'], df['Low'], fast=fast, slow=slow)

def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Average True Range (ATR)
    """
    if df.empty:
        return pd.Series()
    return ta.atr(df['High'], df['Low'], df['Close'], length=length)
