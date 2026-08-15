# Database Usage Audit - Screener Project

## 1. Table Inventory

| Table Name | Status | Usage | Description |
|---|---|---|---|
| `users` | ACTIVE | Backend/Frontend | User auth and balance management. |
| `stock_master` | ACTIVE | Backend/Scanner | Master list of emiten and fundamental data. |
| `price_snapshot` | UNUSED | - | Intended for historical data but currently `ohlcv_cache` is used. |
| `divergence_signal` | ACTIVE | Scanner/API | Latest detected signals from the scanner. |
| `ohlcv_cache` | ACTIVE | Provider | Local cache of Yahoo Finance data to reduce API hits. |

## 2. Usage Audit

### `users`
- **Referenced by**: `app/api/auth.py`, `app/api/users.py`, `app/api/backtest.py`.
- **Status**: KEEP.

### `stock_master`
- **Referenced by**: `app/universe/repository.py`, `app/api/stocks.py`, `app/scanner/engine.py`.
- **Status**: KEEP.

### `price_snapshot`
- **Referenced by**: NOT FOUND in code (only in `scripts/check_tables.py`).
- **Status**: CANDIDATE_FOR_DELETE (but wait until `ohlcv_cache` is promoted/merged).

### `divergence_signal`
- **Referenced by**: `app/api/scanner.py`, `app/scanner/engine.py`.
- **Status**: KEEP.

### `ohlcv_cache`
- **Referenced by**: `app/providers/yfinance_provider.py`.
- **Status**: KEEP (Primary source for historical data).

## 3. Missing Tables (Required by Goal)

| Table Name | Purpose |
|---|---|
| `backtest_runs` | To store history of backtest executions. |
| `backtest_trades` | To store individual trades from backtests for statistical analysis. |
| `strategy_results` | Summary metrics per strategy. |
| `strategy_history` | Historical performance of strategies over time. |

## 4. Cleanup Recommendation

1. **Keep** all ACTIVE tables.
2. **Audit** `price_snapshot` further. If `ohlcv_cache` is sufficient, `price_snapshot` can be dropped or renamed for clarity.
3. **Migrate** to include new backtest and strategy tables.
