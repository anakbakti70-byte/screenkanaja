# Architecture Audit - Screener Project

## 1. Current State Assessment

### Strategy Implementation
- **Bullish Divergence**: Implemented, follows wave structure but needs refinement on Fib levels and strict candle confirmation as per `final.md`.
- **Double Bullish Divergence**: Implemented but logic for "Double" status and SL at Fib 2 needs strict validation.
- **Correction (ABC)**: Implemented, follows Fib 0.6-0.7 zone.
- **Hidden Bullish Divergence**: Implemented, follows A-B-C-D-E structure.

### Data Pipeline
- **Sync Universe**: Exists, merges multiple sources.
- **OHLCV Data**: Currently fetched on-demand from Yahoo Finance with a simple cache. `final.md` requires historical data stored in Supabase and used for all operations.
- **Liquidity Filter**: Implemented (Rp 1 Billion), follows `final.md`.

### Backtest Engine
- **Basic Simulation**: Bar-by-bar simulation exists.
- **Gaps**: Missing transaction costs (fees, tax, slippage), ARA/ARB handling, R-multiple metrics, and statistical validation (p-value).
- **Lookahead Bias**: Current implementation uses `bar['Low']` and `bar['High']` which is acceptable but needs care when SL and TP hit on the same bar (conservative assumption: SL first).

### API & Frontend
- **FastAPI**: Provides endpoints for stocks, scanner results, and on-demand backtests.
- **Supabase**: Used for master data, signals, and OHLCV cache.

## 2. Gap Analysis vs Goal

| Feature | Status | Action Required |
|---|---|---|
| Strategy Truth (`final.md`) | Partial | Align all strategy parameters and confirmation rules strictly. |
| Quantitative Methodology | Missing | Integrate `hermes-idx` style metrics (R-multiple, p-value, bootstrap). |
| Backtest Engine | Basic | Upgrade with Fees, Slippage, ARA/ARB, and strict data isolation. |
| Validation | Missing | Implement Walk-forward and Out-of-sample (OOS) validation. |
| IHSG Regime Filter | Missing | Add IHSG regime detection and integrate as filter/feature. |
| Relative Strength | Missing | Add calculation of RS vs IHSG. |
| Scheduler/Jobs | Basic | Implement robust background jobs for data sync and backtest runs. |
| Automated Cleanup | Missing | Create scripts for safe repository and database cleanup. |

## 3. Planned Improvements

### Phase 1: Core Strategy Refinement
- Update `app/strategies/*.py` to match `final.md` exactly.
- Enforce strict candle confirmation (No Doji, Close only).

### Phase 2: Backtest & Quant Upgrade
- Upgrade `app/backtesting/engine.py` with transaction costs and conservative exit logic.
- Implement `app/backtesting/metrics.py` for R-multiple and Statistical testing.
- Add OOS and Walk-forward logic.

### Phase 3: Data Integrity
- Refactor `YFinanceProvider` to prioritize database over Yahoo Finance.
- Create `scripts/download_ohlcv.py` for proactive historical data collection.

### Phase 4: Risk & Regime
- Implement IHSG Regime detection.
- Implement Relative Strength calculation.
- Integrate these into strategies and scanner.

### Phase 5: Infrastructure & Cleanup
- Implement automated verification tests.
- Run safe cleanup of unused files and tables.
