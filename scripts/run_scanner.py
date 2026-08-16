import asyncio
import sys
import os
from datetime import datetime

# Add apps/backend to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.scanner.engine import ScannerEngine
from app.utils.market import is_idx_market_open

async def main():
    # Scanner Rule: Focus on "Forward Prediction" using fresh data.
    # It only runs when market is open to capture real-time signals.
    if not is_idx_market_open():
        print(f"--- SCANNER SLEEP: Market is Closed ({datetime.now().strftime('%H:%M')}) ---")
        return

    market = os.getenv("SCANNER_MARKET", "idx")
    timeframe = os.getenv("SCANNER_TIMEFRAME", "1d")

    print(f"--- RUNNING SCANNER: {market} ({timeframe}) ---")
    engine = ScannerEngine()

    try:
        results = await engine.run_scan(market=market, timeframe=timeframe)
        print(f"--- SCAN COMPLETED: Found {len(results)} setups ---")
    except Exception as e:
        print(f"--- SCAN FAILED: {e} ---")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
