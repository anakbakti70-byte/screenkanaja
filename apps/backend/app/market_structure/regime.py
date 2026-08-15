import pandas as pd
import numpy as np
from app.providers.yfinance_provider import YFinanceProvider
from app.core.database import supabase

class MarketRegimeDetector:
    def __init__(self):
        self.provider = YFinanceProvider()

    def detect_regime(self, df_ihsg: pd.DataFrame) -> dict:
        """
        Detects IHSG regime based on MA200 and its slope.
        """
        if df_ihsg.empty or len(df_ihsg) < 200:
            return {"regime": "UNKNOWN"}

        df = df_ihsg.copy()
        df['ma200'] = df['Close'].rolling(window=200).mean()

        last_price = df['Close'].iloc[-1]
        ma200 = df['ma200'].iloc[-1]

        # Calculate slope over last 10 days
        ma200_prev = df['ma200'].iloc[-11]
        slope = (ma200 - ma200_prev) / 10 if not pd.isna(ma200_prev) else 0

        if last_price > ma200 and slope > 0:
            regime = "BULLISH"
        elif last_price < ma200 and slope < 0:
            regime = "BEARISH"
        else:
            regime = "NEUTRAL"

        return {
            "date": df.index[-1].date().isoformat(),
            "symbol": "IHSG",
            "ma200": float(ma200),
            "regime": regime,
            "ma200_slope": float(slope)
        }

    async def update_market_regime(self):
        """Fetch IHSG data and update DB."""
        df = self.provider.get_ohlcv("^JKSE", "1d", limit=250)
        if not df.empty:
            regime_data = self.detect_regime(df)
            try:
                supabase.table("market_regime").upsert(regime_data).execute()
                print(f"Market Regime Updated: {regime_data['regime']}")
            except Exception as e:
                print(f"Error saving market regime: {e}")

def calculate_relative_strength(df_stock: pd.DataFrame, df_ihsg: pd.DataFrame) -> pd.Series:
    """
    Calculates Relative Strength of stock vs IHSG.
    Formula: (Stock_Close / IHSG_Close) normalized.
    """
    # Reindex IHSG to match Stock dates
    ihsg_close = df_ihsg['Close'].reindex(df_stock.index).ffill()
    rs = df_stock['Close'] / ihsg_close
    # Optional: Normalize to a baseline (e.g., 100 at start of series)
    if not rs.empty:
        rs = (rs / rs.iloc[0]) * 100
    return rs
