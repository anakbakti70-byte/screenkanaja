from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from app.core.database import supabase
from app.providers.yfinance_provider import YFinanceProvider
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao

router = APIRouter()
provider = YFinanceProvider()

@router.get("/ipo")
async def get_recent_ipos():
    """Returns 10 newest listed stocks."""
    try:
        response = supabase.table("stock_master") \
            .select("*") \
            .order("listing_date", desc=True) \
            .limit(10) \
            .execute()
        return response.data
    except Exception as e:
        print(f"IPO API ERROR: {e}")
        return []

@router.get("/losers")
async def get_top_losers():
    """Returns stocks with lowest prices or potential losers for divergence hunting."""
    try:
        # Fetch active stocks under 1000, ordered by those recently updated
        # In a real scenario, we'd compare vs prev_close.
        # Here we prioritize stocks under 1000 that might be hitting new lows.
        response = supabase.table("stock_master") \
            .select("*") \
            .lte("last_price", 1000) \
            .eq("is_active", True) \
            .order("last_price", desc=False) \
            .limit(10) \
            .execute()
        return response.data
    except Exception as e:
        print(f"LOSERS API ERROR: {e}")
        return []

@router.get("/{symbol}/candles")
async def get_stock_candles(symbol: str, timeframe: str = "1d"):
    """
    Standardized Professional Candle API:
    - 100% Yahoo Finance Alignment
    - Unix Timestamp (seconds)
    - Full OHLCV + AO + RSI
    """
    try:
        clean_symbol = symbol.upper().replace(".JK", "")
        yahoo_symbol = f"{clean_symbol}.JK"

        # Fetch 150 bars for indicator stability
        df = provider.get_ohlcv(yahoo_symbol, timeframe, limit=150)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

        # 1. Calculate Indicators (Bill Williams AO)
        df['rsi_val'] = calculate_rsi(df)
        df['ao_val'] = calculate_ao(df)

        # 2. Normalize Data
        df = df.reset_index()
        time_col = next((c for c in df.columns if c.lower() in ['date', 'datetime', 'ts', 'index']), None)

        candles = []
        for _, row in df.iterrows():
            if pd.isna(row['Close']): continue

            # Use Unix Timestamp in Seconds (Professional Standard)
            ts = int(row[time_col].timestamp())

            candles.append({
                "time": ts,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume']),
                "ao": None if pd.isna(row['ao_val']) else float(row['ao_val']),
                "rsi": None if pd.isna(row['rsi_val']) else float(row['rsi_val'])
            })

        # 3. Professional Response Structure
        return {
            "symbol": clean_symbol,
            "exchange": "IDX",
            "timezone": "Asia/Jakarta",
            "timeframe": timeframe,
            "adjusted": True, # We use auto_adjust from yfinance
            "candles": candles
        }

    except Exception as e:
        print(f"🔥 CANDLE API ERROR [{symbol}]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_stocks(symbol: Optional[str] = None):
    try:
        query = supabase.table("stock_master").select("*").lte("last_price", 1000).eq("is_active", True).order("symbol", desc=False)
        if symbol:
            query = query.ilike("symbol", f"%{symbol}%")
        response = query.execute()
        return response.data
    except Exception as e:
        print(f"STOCKS API ERROR: {e}")
        return []
