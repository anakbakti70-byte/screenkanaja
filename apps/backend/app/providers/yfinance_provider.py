import os
import yfinance as yf
import pandas as pd
import pickle
from datetime import datetime
from .base import BaseDataProvider
from ..core.redis_client import redis_client

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_dir=None, cache_expiry_intraday=300):
        if cache_dir is None:
            # Default to data/cache in project root
            # Assuming we run from project root or apps/backend
            self.cache_dir = os.path.join(os.getcwd(), "data", "cache")
        else:
            self.cache_dir = cache_dir
            
        self.cache_expiry_intraday = cache_expiry_intraday
        
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create cache directory {self.cache_dir}: {e}")

    def _get_parquet_path(self, symbol, timeframe):
        # Sanitize symbol for filename
        safe_symbol = symbol.replace(".", "_").replace("^", "IDX_")
        return os.path.join(self.cache_dir, f"{safe_symbol}_{timeframe}.parquet")

    def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start: datetime = None, 
        end: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:
        
        # 1. Check Redis for Intraday (Timeframes < 1d)
        # yfinance timeframe strings: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        is_intraday = timeframe in ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h"]
        
        # Create a unique cache key for Redis
        redis_key = f"ohlcv:{symbol}:{timeframe}:{start}:{end}:{limit}"
        
        if is_intraday and redis_client:
            try:
                cached_redis = redis_client.get(redis_key)
                if cached_redis:
                    return pickle.loads(cached_redis)
            except Exception as e:
                print(f"Redis error: {e}")

        # 2. Check Parquet for Historical/Daily
        parquet_path = self._get_parquet_path(symbol, timeframe)
        df_cached = pd.DataFrame()
        
        if os.path.exists(parquet_path):
            try:
                df_cached = pd.read_parquet(parquet_path)
            except Exception as e:
                print(f"Parquet read error: {e}")
        
        # 3. Fetch from yfinance
        ticker = yf.Ticker(symbol)
        
        yf_start = start.strftime('%Y-%m-%d') if isinstance(start, datetime) else start
        yf_end = end.strftime('%Y-%m-%d') if isinstance(end, datetime) else end
        
        # If we have cached data and it's daily, we might only need to fetch recent data
        # For MVP, we fetch and merge
        try:
            df = ticker.history(
                start=yf_start,
                end=yf_end,
                interval=timeframe,
                period="max" if not yf_start else None
            )
        except Exception as e:
            print(f"yfinance fetch error for {symbol}: {e}")
            return df_cached # Return cached if fetch fails

        if df.empty:
            return df_cached

        # 4. Merge and Cache
        if not df_cached.empty:
            # Combine and remove duplicates based on index (Datetime)
            df = pd.concat([df_cached, df])
            df = df[~df.index.duplicated(keep='last')].sort_index()
        
        # Save to Parquet
        try:
            df.to_parquet(parquet_path)
        except Exception as e:
            print(f"Parquet write error: {e}")
        
        # Cache to Redis if intraday
        if is_intraday and redis_client:
            try:
                redis_client.setex(redis_key, self.cache_expiry_intraday, pickle.dumps(df))
            except Exception as e:
                print(f"Redis write error: {e}")

        if limit:
            return df.tail(limit)
            
        return df

    def get_last_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        try:
            # Try to get fast_info if available
            return float(ticker.fast_info['lastPrice'])
        except:
            try:
                # Fallback to history
                df = ticker.history(period="1d")
                if not df.empty:
                    return float(df['Close'].iloc[-1])
            except:
                pass
        return 0.0
