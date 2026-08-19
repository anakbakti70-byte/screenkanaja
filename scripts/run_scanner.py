import asyncio
import sys
import os
import time
from datetime import datetime

# Add apps/backend to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.scanner.scanner_core import ScannerEngine, is_idx_market_open

async def main():
    """
    ULTRA REAL-TIME SCANNER LOOP:
    Continuously scans market data from API first, then saves to DB.
    Optimized for IDX market hours with 1s refresh when open.
    """
    market = os.getenv("SCANNER_MARKET", "idx")
    timeframe = os.getenv("SCANNER_TIMEFRAME", "1d")

    print(f"--- 🚀 CTG ULTRA SCANNER STARTED: {market} ({timeframe}) ---")

    engine = ScannerEngine()

    while True:
        try:
            is_open = is_idx_market_open()

            start_time = time.time()
            results = await engine.run_scan(market=market, timeframe=timeframe)
            duration = time.time() - start_time

            timestamp = datetime.now().strftime('%H:%M:%S')
            status_str = "OPEN 🟢" if is_open else "CLOSED 🔴"
            print(f"✅ [{timestamp}] [{status_str}] Scan Complete: {len(results)} active setups in {duration:.2f}s")

            # Realtime 1s check if market is open
            if is_open:
                wait_time = max(0.1, 1.0 - duration)
            else:
                # Slower cycle when market is closed to save API quota/bandwidth
                # but still revalidating occasionally for data integrity.
                wait_time = 60.0

            await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"❌ SCAN ERROR: {e}")
            await asyncio.sleep(10) # Wait longer on error

if __name__ == "__main__":
    asyncio.run(main())
