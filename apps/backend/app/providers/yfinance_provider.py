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
        limit: int = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        HYBRID DATA STRATEGY:
        1. Market Open: API-FIRST (Real-time) -> Save to DB Cache.
        2. Market Closed: DB-FIRST (Static) -> Fallback to API if DB empty.
        """
        clean_symbol = symbol.replace(".JK", "").upper()
        yf_symbol = f"{clean_symbol}.JK"

        from app.scanner.scanner_core import is_idx_market_open
        market_active = is_idx_market_open()

        # --- STEP 1: IF MARKET CLOSED, TRY DB FIRST ---
        if not market_active and use_cache:
            db_df = self._fetch_from_db(clean_symbol, timeframe, limit)
            if not db_df.empty:
                return db_df

        # --- STEP 2: IF MARKET OPEN (OR DB EMPTY), FETCH FROM API ---
        try:
            if market_active:
                print(f"📡 REALTIME API FETCH: {clean_symbol} [{timeframe}]")

            ticker = yf.Ticker(yf_symbol)
            period = "2y" if timeframe == "1d" else "1mo"
            if timeframe in ['1m', '5m', '15m']: period = "5d"

            df = ticker.history(period=period, interval=timeframe, auto_adjust=True)

            if not df.empty:
                # 1s Real-time Price Injection during market hours
                if market_active and timeframe == "1d":
                    try:
                        lp = ticker.fast_info['lastPrice']
                        if lp: df.iloc[-1, df.columns.get_loc('Close')] = lp
                    except: pass

                # --- STEP 3: SYNC TO DATABASE CACHE ---
                self._save_to_cache(clean_symbol, timeframe, df)

                if limit: return df.tail(limit)
                return df

        except Exception as e:
            if market_active:
                print(f"⚠️ API Failed for {clean_symbol}: {e}. Trying DB fallback...")

        # --- STEP 4: FINAL FALLBACK TO DB ---
        return self._fetch_from_db(clean_symbol, timeframe, limit)

    def _fetch_from_db(self, symbol, timeframe, limit):
        try:
            if not supabase: return pd.DataFrame()
            query = supabase.table("ohlcv_cache") \
                .select("*") \
                .eq("symbol", symbol) \
                .eq("timeframe", timeframe) \
                .order("ts", desc=True) \
                .limit(limit or 1000)

            resp = query.execute()
            if resp.data:
                df = pd.DataFrame(resp.data)
                df['ts'] = pd.to_datetime(df['ts'])
                df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                return df.set_index('ts').sort_index()
        except: pass
        return pd.DataFrame()

    def _save_to_cache(self, symbol, timeframe, df):
        if not supabase or df.empty: return

        # Performance: Only save the LATEST bar to DB during high-frequency scans
        # to prevent Supabase 'Request Rate Limit' or lock contention.
        # Historical sync happens once a day via sync_universe.py.
        latest_row = df.iloc[-1]
        ts = df.index[-1]

        data = {
            "symbol": symbol, "timeframe": timeframe, "ts": ts.isoformat(),
            "open": float(latest_row['Open']), "high": float(latest_row['High']),
            "low": float(latest_row['Low']), "close": float(latest_row['Close']),
            "volume": int(latest_row['Volume']),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Atomic upsert for the single latest candle
            supabase.table("ohlcv_cache").upsert(data, on_conflict="symbol,timeframe,ts").execute()

            # Also update stock_master last_price for the dashboard
            supabase.table("stock_master").update({
                "last_price": float(latest_row['Close']),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("symbol", symbol).execute()
        except: pass

    def get_last_price(self, symbol: str) -> float:
        try:
            ticker = yf.Ticker(symbol)
            return float(ticker.fast_info['lastPrice'])
        except: return 0.0
