import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / "apps" / "backend" / ".env"
load_dotenv(env_path)

DB_URI = os.getenv("SUPABASE_URI_SESSIONPOOLER")

SQL_CREATE_TABLES = """
-- 1. Master emiten
CREATE TABLE IF NOT EXISTS stock_master (
    symbol            VARCHAR(20) PRIMARY KEY,
    company_name      VARCHAR(255),
    name              VARCHAR(255),
    listing_date      DATE,
    shares_outstanding BIGINT,
    market_cap        BIGINT,
    last_price        NUMERIC,
    board             VARCHAR(50),
    sector            VARCHAR(100),
    industry          VARCHAR(100),
    description       TEXT,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_synced_at    TIMESTAMP WITH TIME ZONE
);

-- 2. Snapshot harga
CREATE TABLE IF NOT EXISTS price_snapshot (
    id                BIGSERIAL PRIMARY KEY,
    symbol            VARCHAR(20) REFERENCES stock_master(symbol),
    timeframe         VARCHAR(10),
    ts                TIMESTAMP WITH TIME ZONE,
    open              NUMERIC,
    high              NUMERIC,
    low               NUMERIC,
    close             NUMERIC,
    volume            BIGINT,
    UNIQUE(symbol, timeframe, ts)
);

-- 3. Divergence Signal
CREATE TABLE IF NOT EXISTS divergence_signal (
    id                BIGSERIAL PRIMARY KEY,
    symbol            VARCHAR(20) REFERENCES stock_master(symbol),
    market            VARCHAR(10) DEFAULT 'idx',
    timeframe         VARCHAR(10),
    method            VARCHAR(100),
    status            VARCHAR(30),
    entry_price       NUMERIC,
    stop_loss         NUMERIC,
    tp_short          NUMERIC,
    tp_far            NUMERIC,
    risk_reward       NUMERIC,
    indicator_used    TEXT,
    score             NUMERIC,
    metadata          JSONB,
    confirm_candle_ts TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(symbol, method, timeframe)
);

-- 4. Users
CREATE TABLE IF NOT EXISTS users (
    id                BIGSERIAL PRIMARY KEY,
    username          VARCHAR(255) UNIQUE NOT NULL,
    hashed_password   TEXT NOT NULL,
    role              VARCHAR(20) DEFAULT 'user',
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

SQL_MIGRATIONS = [
    ("users", "balance", "NUMERIC DEFAULT 100000000"),
    ("users", "role", "VARCHAR(20) DEFAULT 'user'"),
    ("stock_master", "last_price", "NUMERIC"),
    ("divergence_signal", "market", "VARCHAR(10) DEFAULT 'idx'"),
    ("divergence_signal", "risk_reward", "NUMERIC"),
    ("divergence_signal", "tp_far", "NUMERIC")
]

SQL_INSERT_ADMIN = """
INSERT INTO users (username, hashed_password, balance)
SELECT 'admin', '$2b$12$6uX7e5M8p6M5Zk/P1z9/8O6vL.YxZ7X3U1Z8u7z8Y7y6v5u4t3s2r', 100000000
WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');
"""

def setup_database():
    if not DB_URI:
        print("❌ Error: SUPABASE_URI_SESSIONPOOLER not found in .env")
        return

    try:
        print(f"🔗 Connecting to Supabase...")
        conn = psycopg2.connect(DB_URI)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("🛠️ Creating tables if not exist...")
            cur.execute(SQL_CREATE_TABLES)

            print("📈 Checking for missing columns (Migrations)...")
            for table, col, col_type in SQL_MIGRATIONS:
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                       WHERE table_name='{table}' AND column_name='{col}') THEN
                            ALTER TABLE {table} ADD COLUMN {col} {col_type};
                        END IF;
                    END $$;
                """)

            print("👤 Ensuring admin user exists...")
            cur.execute(SQL_INSERT_ADMIN)

            print("✅ Database schema verified and updated.")
        conn.close()
    except Exception as e:
        print(f"❌ Database Setup Error: {e}")

if __name__ == "__main__":
    setup_database()
