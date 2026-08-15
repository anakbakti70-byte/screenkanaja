# Screener - Professional Quantitative Trading Platform

## 🚀 Overview
Screener is a high-performance trading platform for IDX stocks, strictly following the **Divergence Method (CTG)** as specified in `final.md`. It combines deterministic price-action analysis with advanced quantitative validation.

## 📖 Strategy Truth (`final.md`)
The system strictly enforces the following methods:
- **Method 1**: Regular Bullish Divergence (1-2-3-4-5 Waves)
- **Method 1B**: Double Bullish Divergence (Max 2, No Triple)
- **Method 2**: Correction (ABC)
- **Method 3**: Hidden Bullish Divergence (ABCDE Continuation)

## 🛠️ Quantitative Methodology
Integrated from `hermes-idx` methodology:
- **Realistic Backtesting**: Includes transaction fees, tax, and slippage.
- **Auto-Rejection (ARA/ARB)**: Prevents unrealistic entries and exits.
- **Statistical Validation**: Bootstrap p-value, Expectancy (R), and Profit Factor.
- **Walk-Forward & OOS**: Multi-stage validation to prevent overfitting.

## 🏗️ Architecture
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Frontend**: React (TypeScript) + Tailwind CSS
- **Indicators**: AO (Priority), MACD, RSI (Deterministic Python)
- **AI Explanation**: LLM-powered reasoning for validated signals.

## 🧹 Automated Maintenance
- `scripts/audit_repository.py`: Identifies unneeded files.
- `scripts/audit_database.py`: Audits Supabase schema and usage.
- `scripts/cleanup_repository.py`: Safely removes artifacts and unused code.
- `scripts/download_stocks.py`: Proactive historical data sync.

## 📄 Documentation
- `ARCHITECTURE_AUDIT.md`: Detailed system assessment.
- `DATABASE_USAGE_AUDIT.md`: Schema usage and cleanup candidates.
- `CLEANUP_PLAN.md`: Protocol for safe repository cleaning.
- `final.md`: The immutable strategy specification.
