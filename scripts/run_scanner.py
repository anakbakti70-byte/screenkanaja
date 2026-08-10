import asyncio
import sys
import os

# Add apps/backend to sys.path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.scanner.engine import ScannerEngine

async def main():
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
