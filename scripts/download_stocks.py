import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import logging

# Ensure backend app is importable
sys.path.append(str(Path(__file__).parent.parent / "apps" / "backend"))

from app.core.database import supabase
from app.providers.yfinance_provider import YFinanceProvider

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def download_universe_data():
    """
    Downloads historical data for all stocks with price < 1000.
    """
    provider = YFinanceProvider()

    # 1. Get Universe
    try:
        resp = supabase.table("stock_master").select("symbol").lte("last_price", 1000).eq("is_active", True).execute()
        symbols = [r['symbol'] for r in resp.data]
        logging.info(f"Discovered {len(symbols)} stocks to download.")
    except Exception as e:
        logging.error(f"Failed to fetch universe: {e}")
        return

    # 2. Download 1d data for all
    for i, symbol in enumerate(symbols):
        try:
            logging.info(f"[{i+1}/{len(symbols)}] Downloading {symbol}...")
            # provider.get_ohlcv will automatically save to cache
            df = provider.get_ohlcv(symbol, "1d")
            if not df.empty:
                logging.info(f"   Successfully saved {len(df)} bars for {symbol}")
            else:
                logging.warning(f"   No data found for {symbol}")
        except Exception as e:
            logging.error(f"   Error downloading {symbol}: {e}")

if __name__ == "__main__":
    download_universe_data()
