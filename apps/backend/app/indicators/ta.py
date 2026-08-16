"""
Indikator momentum sesuai final.md §2. SEMUA dihitung dengan kode/matematika
deterministik -- final.md §0 tegas: "Kalkulasi ... = matematika deterministik
-> wajib dihitung pakai kode (Python/SQL), bukan ditebak oleh LLM".

Urutan pengecekan divergence di strategi (final.md §2): AO dulu -> MACD -> RSI.
Cukup SATU yang confirm, tidak perlu ketiganya sepakat.
"""

import pandas as pd
import numpy as np

REQUIRED_OHLC_COLS = {"Open", "High", "Low", "Close"}


def _validate_ohlc(df: pd.DataFrame, needed: set) -> bool:
    return not df.empty and needed.issubset(df.columns)


def calculate_ao(df: pd.DataFrame, fast: int = 5, slow: int = 34) -> pd.Series:
    """
    Awesome Oscillator (AO) - formula resmi Bill Williams.
    Median Price = (High + Low) / 2
    AO = SMA(Median Price, 5) - SMA(Median Price, 34)

    final.md §2: "ubah style dari histogram -> line agar mudah dibaca" --
    itu murni preferensi tampilan chart, tidak mengubah nilai/perhitungan AO
    itu sendiri, jadi tidak berpengaruh ke fungsi ini.
    """
    if not _validate_ohlc(df, {"High", "Low"}):
        return pd.Series(dtype="float64")

    median_price = (df["High"] + df["Low"]) / 2
    sma_fast = median_price.rolling(window=fast).mean()
    sma_slow = median_price.rolling(window=slow).mean()
    return sma_fast - sma_slow


def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """RSI dengan smoothing Wilder (EWM alpha=1/length), setting default final.md §2."""
    if not _validate_ohlc(df, {"Close"}):
        return pd.Series(dtype="float64")

    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / length, adjust=False).mean()

    # Hindari div-by-zero: kalau loss=0 terus-menerus, RSI = 100 (bukan NaN/inf).
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(100.0)
    return rsi


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD standar (EMA 12/26, signal EMA 9), setting default final.md §2."""
    if not _validate_ohlc(df, {"Close"}):
        return pd.DataFrame(columns=["macd", "signal", "hist"])

    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def calculate_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """
    Average True Range (ATR) -- dipakai PivotDetector (bukan bagian dari §2,
    tapi jadi dasar deteksi swing high/low di app/market_structure/pivots.py).
    """
    if not _validate_ohlc(df, {"High", "Low", "Close"}):
        return pd.Series(dtype="float64")

    high, low = df["High"], df["Low"]
    close_prev = df["Close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)

    return tr.ewm(alpha=1 / length, min_periods=length, adjust=False).mean()
