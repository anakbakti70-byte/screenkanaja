import os
import sys
import time
import psycopg2
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "apps" / "backend" / ".env")
DB_URI = os.getenv("SUPABASE_URI_SESSIONPOOLER")

def run_janitor():
    if not DB_URI: return

    print(f"🧹 [Worker 3] Ultra DB Maintenance Starting: {datetime.now()}")
    try:
        conn = psycopg2.connect(DB_URI)
        conn.autocommit = True
        with conn.cursor() as cur:
            # 1. Hapus Cache yang tidak terpakai (Data lebih dari 1 hari untuk Intraday/Daily)
            # Karena sistem API-First, cache hanya cadangan singkat.
            cur.execute("DELETE FROM ohlcv_cache WHERE ts < NOW() - INTERVAL '1 day';")

            # 2. Prune Old Signals (Keep only 7 days for historical review)
            cur.execute("DELETE FROM divergence_signal WHERE created_at < NOW() - INTERVAL '7 days' AND status NOT IN ('READY', 'VALID');")

            print(f"✨ [Worker 3] Stale Cache and Old Signals removed successfully.")
        conn.close()
    except Exception as e:
        print(f"❌ [Worker 3] Janitor Error: {e}")

if __name__ == "__main__":
    while True:
        run_janitor()
        # Run once a day
        print("😴 [Worker 3] Sleeping for 24 hours...")
        time.sleep(86400)
