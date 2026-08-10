import os
import yfinance as yf
import pandas as pd
import pickle
from datetime import datetime, timezone
from .base import BaseDataProvider
from ..core.redis_client import redis_client
from ..core.database import supabase

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_dir=None, cache_expiry_intraday=300):
        if cache_dir is None:
            self.cache_dir = os.path.join(os.getcwd(), "data", "cache")
        else:
            self.cache_dir = cache_dir
            
        self.cache_expiry_intraday = cache_expiry_intraday
        
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create cache directory {self.cache_dir}: {e}")

    def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start: datetime = None, 
        end: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:

        clean_symbol = symbol.replace(".JK", "").upper()
        
        # 1. Try fetching from Supabase 'price_snapshot' first
        try:
            if supabase:
                query = supabase.table("price_snapshot").select("*").eq("symbol", clean_symbol).eq("timeframe", timeframe).order("ts", desc=True)
                if limit: query = query.limit(limit)

                resp = query.execute()
                if resp.data and len(resp.data) > 20:
                    df_db = pd.DataFrame(resp.data)
                    df_db['ts'] = pd.to_datetime(df_db['ts'])
                    df_db = df_db.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                    })
                    df_db = df_db.set_index('ts').sort_index()
                    # Return if we have enough recent data (last 24h)
                    last_ts = df_db.index[-1]
                    if (datetime.now(timezone.utc) - last_ts.to_pydatetime()).total_seconds() < 3600:
                        return df_db
        except Exception as e:
            print(f"DB Fetch Error for {symbol}: {e}")

        # 2. Fetch from yfinance if DB is empty or stale
        ticker = yf.Ticker(symbol)
        try:
            df = ticker.history(period="1y" if not limit or limit > 100 else "1mo", interval=timeframe)
            if not df.empty:
                # Cache to DB in background (simplified here)
                self._save_to_db(clean_symbol, timeframe, df)
                if limit: return df.tail(limit)
                return df
        except Exception as e:
            print(f"yfinance fetch error for {symbol}: {e}")

        return pd.DataFrame()

    def _save_to_db(self, symbol, timeframe, df):
        if not supabase or df.empty: return
        
        data = []
        # Take last 100 bars to avoid heavy payload
        df_save = df.tail(100)
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
            supabase.table("price_snapshot").upsert(data, on_conflict="symbol,timeframe,ts").execute()
        except:
            pass

    def get_last_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        try:
            return float(ticker.fast_info['lastPrice'])
        except:
            return 0.0
