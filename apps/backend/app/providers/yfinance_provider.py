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
        """
        Priority:
        1. DB Cache (ohlcv_cache)
        2. Yahoo Finance (and then save to DB)
        """
        clean_symbol = symbol.replace(".JK", "").upper()
        
        # 1. Fetch from DB
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
                    query = query.limit(1000) # Increased limit for backtesting

                resp = query.execute()
                if resp.data:
                    df_db = pd.DataFrame(resp.data)
                    df_db['ts'] = pd.to_datetime(df_db['ts'])
                    df_db = df_db.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                    })
                    df_db = df_db.set_index('ts').sort_index()

                    # If we have enough data and it's not a live request, return it
                    if len(df_db) >= (limit or 100):
                        # For 1d timeframe, check if we need today's update
                        if timeframe == "1d":
                            last_ts = df_db.index[-1].date()
                            today = datetime.now(timezone.utc).date()
                            if last_ts >= today:
                                return df_db
                        else:
                            return df_db
        except Exception as e:
            print(f"DB Fetch Error for {symbol}: {e}")

        # 2. Fetch from yfinance
        print(f"Enriching {clean_symbol} from Yahoo Finance...")
        ticker = yf.Ticker(f"{clean_symbol}.JK")
        try:
            period = "2y" if timeframe == "1d" else "1mo"
            df = ticker.history(period=period, interval=timeframe)

            if not df.empty:
                self._save_to_cache(clean_symbol, timeframe, df)
                if limit: return df.tail(limit)
                return df
        except Exception as e:
            print(f"yfinance fetch error for {symbol}: {e}")

        return pd.DataFrame()

    def _save_to_cache(self, symbol, timeframe, df):
        if not supabase or df.empty: return

        data = []
        for ts, row in df.iterrows():
            # Handle possible NaNs from yfinance
            if pd.isna(row['Close']): continue

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
            # Upsert in chunks to avoid request size limits
            chunk_size = 100
            for i in range(0, len(data), chunk_size):
                supabase.table("ohlcv_cache").upsert(
                    data[i:i+chunk_size],
                    on_conflict="symbol,timeframe,ts"
                ).execute()
        except Exception as e:
            print(f"Error saving cache for {symbol}: {e}")

    def get_last_price(self, symbol: str) -> float:
        ticker = yf.Ticker(symbol)
        try:
            return float(ticker.fast_info['lastPrice'])
        except:
            return 0.0
