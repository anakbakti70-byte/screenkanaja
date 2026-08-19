import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import yfinance as yf

# Add apps/backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.core.database import supabase
from app.scanner.scanner_core import is_idx_market_open

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "apps" / "backend" / ".env")

def update_market_data_realtime():
    """
    Worker 2: High-Frequency Sync (1s interval during market hours).
    Ensures data exists in DB even if market just closed.
    """
    market_active = is_idx_market_open()

    # Allow a 30-min window after close to ensure EOD sync
    now = datetime.now()
    if not market_active:
        if now.hour == 16 and now.minute <= 30:
            print("🕒 Market recently closed. Final EOD Sync...")
        else:
            return False

    try:
        # Fetch active stocks under 1000
        res = supabase.table("stock_master").select("symbol").eq("is_active", True).lte("last_price", 1000).execute()
        symbols = [s['symbol'] for s in res.data]
        if not symbols: return True

        yf_symbols = [f"{s}.JK" for s in symbols]

        # Use period="5d" instead of "1d" to ensure we get data even for illiquid stocks
        # and disable threads to avoid sqlite 'database is locked' errors
        data = yf.download(
            tickers=yf_symbols,
            period="5d",
            interval="1m",
            group_by='ticker',
            auto_adjust=True,
            threads=False,
            progress=False
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        for symbol in symbols:
            try:
                yf_sym = f"{symbol}.JK"
                if yf_sym in data.columns.levels[0]:
                    ticker_data = data[yf_sym].dropna()
                    if not ticker_data.empty:
                        last_price = float(ticker_data['Close'].iloc[-1])
                        supabase.table("stock_master").update({"last_price": last_price, "updated_at": now_iso}).eq("symbol", symbol).execute()
            except: continue
        return True
    except Exception as e:
        print(f"❌ Worker Error: {e}")
        return True

if __name__ == "__main__":
    while True:
        is_running = update_market_data_realtime()
        # Ultra real-time: 0.1s delay when market is active
        wait_time = 0.1 if is_running else 300
        time.sleep(wait_time)
