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
    signal_id         VARCHAR(255) UNIQUE, -- symbol:method:timeframe:pattern_idx:entry_idx
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
    confidence        NUMERIC DEFAULT 0,
    pattern_candle_index INTEGER,
    entry_candle_index   INTEGER,
    signal_age        INTEGER DEFAULT 0,
    reason            TEXT,
    metadata          JSONB,
    confirm_candle_ts TIMESTAMP WITH TIME ZONE,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(symbol, method, timeframe, pattern_candle_index, entry_candle_index)
);

-- 4. Cache Khusus (Hemat Database)
CREATE TABLE IF NOT EXISTS ohlcv_cache (
    symbol            VARCHAR(20),
    timeframe         VARCHAR(10),
    ts                TIMESTAMP WITH TIME ZONE,
    open              NUMERIC,
    high              NUMERIC,
    low               NUMERIC,
    close             NUMERIC,
    volume            BIGINT,
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (symbol, timeframe, ts)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_cache_ts ON ohlcv_cache (ts DESC);

-- 5. Users (Ensure balance is Rp 1 Trillion)
-- Note: users.id might already be UUID from Supabase Auth
CREATE TABLE IF NOT EXISTS users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username          VARCHAR(255) UNIQUE NOT NULL,
    hashed_password   TEXT NOT NULL,
    role              VARCHAR(20) DEFAULT 'user',
    balance           NUMERIC DEFAULT 1000000000000,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 6. Backtest Sessions
CREATE TABLE IF NOT EXISTS backtest_sessions (
    id                BIGSERIAL PRIMARY KEY,
    user_id           UUID REFERENCES users(id),
    name              VARCHAR(255),
    initial_balance   NUMERIC DEFAULT 1000000000000,
    current_balance   NUMERIC DEFAULT 1000000000000,
    status            VARCHAR(20) DEFAULT 'ACTIVE',
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 7. Backtest Positions
CREATE TABLE IF NOT EXISTS backtest_positions (
    id                BIGSERIAL PRIMARY KEY,
    session_id        BIGINT REFERENCES backtest_sessions(id) ON DELETE CASCADE,
    symbol            VARCHAR(20),
    avg_price         NUMERIC,
    quantity          BIGINT,
    stop_loss         NUMERIC,
    take_profit        NUMERIC,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(session_id, symbol)
);

-- 8. Backtest Orders
CREATE TABLE IF NOT EXISTS backtest_orders (
    id                BIGSERIAL PRIMARY KEY,
    session_id        BIGINT REFERENCES backtest_sessions(id) ON DELETE CASCADE,
    symbol            VARCHAR(20),
    side              VARCHAR(10),
    order_type        VARCHAR(20),
    quantity          BIGINT,
    price             NUMERIC,
    stop_loss         NUMERIC,
    take_profit        NUMERIC,
    status            VARCHAR(20) DEFAULT 'PENDING',
    source            VARCHAR(50),
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
    filled_at         TIMESTAMP WITH TIME ZONE
);

-- 9. Backtest Transactions
CREATE TABLE IF NOT EXISTS backtest_transactions (
    id                BIGSERIAL PRIMARY KEY,
    session_id        BIGINT REFERENCES backtest_sessions(id) ON DELETE CASCADE,
    symbol            VARCHAR(20),
    side              VARCHAR(10),
    quantity          BIGINT,
    price             NUMERIC,
    gross_amount      NUMERIC,
    fee               NUMERIC,
    net_amount        NUMERIC,
    realized_pnl      NUMERIC,
    realized_pnl_pct  NUMERIC,
    source            VARCHAR(50), -- MANUAL, STRATEGY
    exit_reason       VARCHAR(50), -- MANUAL, STOP_LOSS, TAKE_PROFIT, TIMEOUT
    ts                TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 10. Portfolio Snapshots
CREATE TABLE IF NOT EXISTS backtest_portfolio_snapshots (
    id                BIGSERIAL PRIMARY KEY,
    session_id        BIGINT REFERENCES backtest_sessions(id) ON DELETE CASCADE,
    ts                TIMESTAMP WITH TIME ZONE DEFAULT now(),
    cash_balance      NUMERIC,
    market_value      NUMERIC,
    total_equity      NUMERIC
);
"""

SQL_MIGRATIONS = [
    ("users", "balance", "NUMERIC DEFAULT 1000000000000"),
    ("stock_master", "last_price", "NUMERIC"),
    ("divergence_signal", "market", "VARCHAR(10) DEFAULT 'idx'"),
    ("divergence_signal", "risk_reward", "NUMERIC"),
    ("divergence_signal", "tp_far", "NUMERIC"),
    ("divergence_signal", "confidence", "NUMERIC DEFAULT 0"),
    ("divergence_signal", "entry_zone_low", "NUMERIC"),
    ("divergence_signal", "entry_zone_high", "NUMERIC"),
    ("divergence_signal", "pattern_candle_index", "INTEGER"),
    ("divergence_signal", "entry_candle_index", "INTEGER"),
    ("divergence_signal", "signal_age", "INTEGER DEFAULT 0"),
    ("divergence_signal", "reason", "TEXT"),
    ("backtest_transactions", "source", "VARCHAR(50)"),
    ("divergence_signal", "signal_id", "VARCHAR(255) UNIQUE")
]

def update_unique_constraint(cur):
    """Updates the unique constraint for divergence_signal to be more granular."""
    try:
        print("🧹 Cleaning up duplicates in divergence_signal before updating constraint...")
        # 1. Hapus duplikat (keep only one)
        cur.execute("""
            DELETE FROM divergence_signal a
            USING divergence_signal b
            WHERE a.id < b.id
            AND a.symbol = b.symbol
            AND a.method = b.method
            AND a.timeframe = b.timeframe
            AND a.pattern_candle_index = b.pattern_candle_index
            AND COALESCE(a.entry_candle_index, -1) = COALESCE(b.entry_candle_index, -1);
        """)

        # 2. Drop old constraint
        cur.execute("ALTER TABLE divergence_signal DROP CONSTRAINT IF EXISTS divergence_signal_symbol_method_timeframe_key;")

        # 3. Add new constraint
        cur.execute("ALTER TABLE divergence_signal DROP CONSTRAINT IF EXISTS divergence_signal_unique_instance;")
        cur.execute("ALTER TABLE divergence_signal ADD CONSTRAINT divergence_signal_unique_instance UNIQUE (symbol, method, timeframe, pattern_candle_index, entry_candle_index);")

        print("✅ Granular unique constraint added to divergence_signal.")
    except Exception as e:
        print(f"⚠️ Could not update unique constraint: {e}")

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
            # We wrap table creation in try-except if user_id type mismatch happens
            cur.execute(SQL_CREATE_TABLES)

            print("📈 Checking for missing columns (Migrations)...")
            for table, col, col_type in SQL_MIGRATIONS:
                try:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
                except psycopg2.errors.DuplicateColumn:
                    pass
                except Exception as e:
                    print(f"⚠️ Migration Error ({table}.{col}): {e}")

            update_unique_constraint(cur)

            print("✅ Database schema verified and updated.")
        conn.close()
    except Exception as e:
        print(f"❌ Database Setup Error: {e}")

if __name__ == "__main__":
    setup_database()
