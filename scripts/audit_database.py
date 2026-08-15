import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / "apps" / "backend" / ".env"
load_dotenv(env_path)

DB_URI = os.getenv("SUPABASE_URI_SESSIONPOOLER")

def audit_database():
    if not DB_URI:
        print("❌ Error: SUPABASE_URI_SESSIONPOOLER not found")
        return

    try:
        conn = psycopg2.connect(DB_URI)
        with conn.cursor() as cur:
            # 1. List all tables
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            tables = [r[0] for r in cur.fetchall()]

            print("--- Database Audit ---")
            active_tables = ['users', 'stock_master', 'divergence_signal', 'ohlcv_cache',
                             'backtest_runs', 'backtest_trades', 'strategy_history', 'market_regime']

            for table in tables:
                status = "KEEP" if table in active_tables else "UNKNOWN/UNUSED"

                # Get row count
                cur.execute(f"SELECT count(*) FROM {table}")
                count = cur.fetchone()[0]

                print(f"[{status}] {table}: {count} rows")

                if status == "UNKNOWN/UNUSED":
                    print(f"  -> Candidate for deletion if not used by any logic.")

        conn.close()
    except Exception as e:
        print(f"❌ Audit Error: {e}")

if __name__ == "__main__":
    audit_database()
