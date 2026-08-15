-- Backtest Runs
CREATE TABLE IF NOT EXISTS backtest_runs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy          VARCHAR(100),
    strategy_version  VARCHAR(20),
    symbol            VARCHAR(20),
    timeframe         VARCHAR(10),
    run_date          TIMESTAMP WITH TIME ZONE DEFAULT now(),
    data_start        TIMESTAMP WITH TIME ZONE,
    data_end          TIMESTAMP WITH TIME ZONE,
    trade_count       INT,
    win_rate          NUMERIC,
    expectancy        NUMERIC, -- in R
    profit_factor     NUMERIC,
    max_drawdown      NUMERIC,
    p_value           NUMERIC,
    sample_size       INT,
    verdict           VARCHAR(30), -- PROVEN_POSITIVE, NOT_PROVEN, etc.
    metadata          JSONB
);

-- Backtest Trades
CREATE TABLE IF NOT EXISTS backtest_trades (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
    symbol            VARCHAR(20),
    strategy          VARCHAR(100),
    timeframe         VARCHAR(10),
    entry_date        TIMESTAMP WITH TIME ZONE,
    exit_date         TIMESTAMP WITH TIME ZONE,
    entry_price       NUMERIC,
    exit_price        NUMERIC,
    stop_loss         NUMERIC,
    take_profit       NUMERIC,
    position_size     INT,
    gross_pnl         NUMERIC,
    fees              NUMERIC,
    tax               NUMERIC,
    slippage          NUMERIC,
    net_pnl           NUMERIC,
    r_multiple        NUMERIC,
    exit_reason       VARCHAR(50),
    bars_held         INT
);

-- Strategy History (to track decay)
CREATE TABLE IF NOT EXISTS strategy_history (
    id                BIGSERIAL PRIMARY KEY,
    strategy          VARCHAR(100),
    date              DATE DEFAULT CURRENT_DATE,
    expectancy        NUMERIC,
    profit_factor     NUMERIC,
    p_value           NUMERIC,
    max_drawdown      NUMERIC,
    sample_size       INT,
    verdict           VARCHAR(30),
    UNIQUE(strategy, date)
);

-- IHSG Regime
CREATE TABLE IF NOT EXISTS market_regime (
    date              DATE PRIMARY KEY,
    symbol            VARCHAR(20) DEFAULT 'IHSG',
    ma200             NUMERIC,
    regime            VARCHAR(20), -- BULLISH, NEUTRAL, BEARISH
    ma200_slope       NUMERIC
);
