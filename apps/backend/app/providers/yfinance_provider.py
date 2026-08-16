import yfinance as yf
import pandas as pd
from datetime import datetime, timezone
from .base import BaseDataProvider
from ..core.database import supabase
from ..core.market_utils import is_idx_market_open

class YFinanceProvider(BaseDataProvider):
    def __init__(self, cache_expiry_intraday=300):
        self.cache_expiry_intraday = cache_expiry_intraday

    def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start: datetime = None, 
        end: datetime = None,
        limit: int = None,
        use_cache: bool = False
    ) -> pd.DataFrame:
        """
        Priority Strategy:
        - MARKET OPEN: Fetch REALTIME from Yahoo (1s accuracy) -> Update Cache -> Return.
        - MARKET CLOSED: Fetch from DB CACHE (data from last close) -> Return.
        """
        clean_symbol = symbol.replace(".JK", "").upper()
        market_is_active = is_idx_market_open()

        # --- PATH A: MARKET IS OPEN (Realtime Mode) ---
        if market_is_active:
            print(f"🚀 MARKET OPEN: Fetching 1s REALTIME data for {clean_symbol}...")
            ticker = yf.Ticker(f"{clean_symbol}.JK")
            try:
                period = "2y" if timeframe == "1d" else "1mo"
                df = ticker.history(period=period, interval=timeframe)

                if not df.empty:
                    self._save_to_cache(clean_symbol, timeframe, df)
                    if limit: return df.tail(limit)
                    return df
                print(f"⚠️ Yahoo returned empty for {clean_symbol}, falling back to cache...")
            except Exception as e:
                print(f"❌ Realtime Fetch Error for {symbol}: {e}")

        # --- PATH B: MARKET IS CLOSED OR REALTIME FAILED (Cache Mode) ---
        if not market_is_active:
            print(f"😴 MARKET CLOSED: Loading {clean_symbol} data from Database Cache...")

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
                    query = query.limit(1000)

                resp = query.execute()
                if resp.data:
                    df_db = pd.DataFrame(resp.data)
                    df_db['ts'] = pd.to_datetime(df_db['ts'])
                    df_db = df_db.rename(columns={
                        'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'
                    })
                    df_db = df_db.set_index('ts').sort_index()
                    return df_db

                if not market_is_active:
                    print(f"❓ No cache found for {clean_symbol} in DB.")
        except Exception as e:
            print(f"❌ DB Cache Fetch Error for {symbol}: {e}")

        # --- PATH C: FINAL FALLBACK (Only if market is active but cache and initial fetch failed) ---
        if market_is_active:
             # Try one last time without high expectations
             return pd.DataFrame()

        return pd.DataFrame()

    def _save_to_cache(self, symbol, timeframe, df):
        if not supabase or df.empty: return

        data = []
        for ts, row in df.iterrows():
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
