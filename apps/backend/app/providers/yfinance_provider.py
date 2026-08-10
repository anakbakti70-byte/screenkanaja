import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from .base import BaseDataProvider
from ..core.database import supabase

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_expiry_intraday=300):
        self.cache_expiry_intraday = cache_expiry_intraday

    def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start: datetime = None, 
        end: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:

        clean_symbol = symbol.replace(".JK", "").upper()
        
        # 1. Try fetching from Supabase 'ohlcv_cache' first
        try:
            if supabase:
                query = supabase.table("ohlcv_cache") \
                    .select("*") \
                    .eq("symbol", clean_symbol) \
                    .eq("timeframe", timeframe) \
                    .order("ts", desc=True)

                if limit:
                    query = query.limit(limit)
                else:
                    query = query.limit(200) # Default cache limit for efficiency

                resp = query.execute()
                if resp.data and len(resp.data) > 10:
                    df_db = pd.DataFrame(resp.data)
                    df_db['ts'] = pd.to_datetime(df_db['ts'])
                    df_db = df_db.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                    })
                    df_db = df_db.set_index('ts').sort_index()

                    # Check if data is fresh (last candle < 1h old for 1d)
                    last_ts = df_db.index[-1]
                    if (datetime.now(timezone.utc) - last_ts.to_pydatetime()).total_seconds() < 3600:
                        return df_db
        except Exception as e:
            print(f"Cache Fetch Error for {symbol}: {e}")

        # 2. Fetch from yfinance if Cache is empty or stale
        ticker = yf.Ticker(symbol)
        try:
            # For 1d, fetch 1y. For intraday, fetch 1mo.
            period = "1y" if timeframe == "1d" else "1mo"
            df = ticker.history(period=period, interval=timeframe)

            if not df.empty:
                # Cache to DB and prune old data
                self._save_to_cache(clean_symbol, timeframe, df)
                if limit: return df.tail(limit)
                return df
        except Exception as e:
            print(f"yfinance fetch error for {symbol}: {e}")

        return pd.DataFrame()

    def _save_to_cache(self, symbol, timeframe, df):
        if not supabase or df.empty: return

        # Take last 200 bars to keep DB lean (Standard & Efficient)
        df_save = df.tail(200)
        data = []
        for ts, row in df_save.iterrows():
            data.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "ts": ts.isoformat(),
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume'])
            })

        try:
            # UPSERT to dedicated cache table
            supabase.table("ohlcv_cache").upsert(data, on_conflict="symbol,timeframe,ts").execute()

            # Optional: Pruning logic could be here, but limiting upsert to 200 is usually enough
            # unless we want to delete bars older than 200 explicitly.
        except Exception as e:
            print(f"Error saving cache for {symbol}: {e}")

    def get_last_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        try:
            return float(ticker.fast_info['lastPrice'])
        except:
            return 0.0
