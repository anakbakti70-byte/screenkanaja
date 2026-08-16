from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.backtesting.engine import BacktestEngineV4
from app.providers.yfinance_provider import YFinanceProvider
from app.core.database import supabase
from app.core.market_utils import is_idx_market_open, Fees
from .auth import get_current_user

router = APIRouter()
provider = YFinanceProvider()

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    initial_capital: float = 100000000
    risk_per_trade: float = 1.0 # Percentage of balance
    buy_fee: Optional[float] = 0.0019
    sell_fee: Optional[float] = 0.0029
    slippage_pct: Optional[float] = 0.001

import numpy as np
import math

def make_json_safe(data):
    """Recursively convert NaN/Inf and numpy types to JSON-safe values."""
    if isinstance(data, dict):
        return {k: make_json_safe(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_safe(v) for v in data]
    elif isinstance(data, (float, np.float64, np.float32)):
        if math.isnan(data) or np.isnan(data):
            return 0.0
        if math.isinf(data) or np.isinf(data):
            return "∞"
        return float(data)
    elif isinstance(data, (int, np.int64, np.int32, np.uint64, np.uint32)):
        return int(data)
    elif hasattr(data, 'isoformat'):
        return data.isoformat()
    return data

@router.post("/run")
async def run_backtest(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Restriction: Real-time backtest only allowed during specified market hours
        if not is_idx_market_open():
             raise HTTPException(
                status_code=403,
                detail="Fitur Backtest Real-time hanya aktif pada jam bursa IDX (Senin-Jumat, 08:45-12:00 & 12:55-17:00). Silakan coba lagi saat bursa buka."
            )

        symbol = req.symbol.upper()
        # Ensure we always use .JK for yfinance to get realtime/latest data
        provider_symbol = f"{symbol}.JK" if ".JK" not in symbol else symbol

        # Force fetch from yfinance by ignoring cache to get realtime data
        print(f"DEBUG: Fetching latest REALTIME data for {provider_symbol}...")
        df = provider.get_ohlcv(provider_symbol, req.timeframe, limit=1000, use_cache=False)

        if df.empty:
            raise HTTPException(status_code=404, detail=f"Data historis tidak ditemukan untuk {symbol}")

        if len(df) < 50:
            raise HTTPException(status_code=400, detail=f"Data historis terlalu sedikit ({len(df)} bar) untuk {symbol}. Butuh minimal 50 bar.")

        print(f"DEBUG: Running backtest engine for {symbol}...")

        # Run Engine
        engine = BacktestEngineV4(
            initial_balance=req.initial_capital,
            risk_per_trade_pct=req.risk_per_trade
        )

        engine.fees = Fees(
            buy_pct=req.buy_fee,
            sell_pct=req.sell_fee,
            slippage_pct=req.slippage_pct
        )

        results = engine.run(df, symbol, req.timeframe)

        # Handle Engine Errors
        if results is None:
            raise HTTPException(status_code=500, detail="Engine returned None")

        if "error" in results:
            raise HTTPException(status_code=400, detail=results["error"])

        # Force key 'candles' for frontend compatibility
        if "history_candles" in results:
            results["candles"] = results.pop("history_candles")
        elif "candles" not in results:
             # Ensure there is at least an empty list
             results["candles"] = []

        # Sanitize results for JSON serialization (convert NaN/Inf/Numpy)
        safe_results = make_json_safe(results)

        # Versioning marker
        safe_results["engine_version"] = "V4.4.2-STABLE"
        safe_results["_debug_info"] = "BACKTEST_API_V4_FINAL"

        print(f"DEBUG: Backtest completed for {symbol}. Candle count: {len(safe_results.get('candles', []))}")

        return safe_results
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"BACKTEST CRITICAL ERROR: {e}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/symbols")
async def get_backtest_symbols(query: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Returns list of symbols available for backtest."""
    try:
        # Fetch all active symbols from Supabase
        db_query = supabase.table("stock_master").select("symbol, company_name, last_price").eq("is_active", True)

        if query:
            db_query = db_query.ilike("symbol", f"%{query}%")

        # Sort by symbol and remove the .limit(100) to show all or increase it significantly
        response = db_query.order("symbol").execute()
        return response.data
    except Exception as e:
        print(f"SYMBOL FETCH ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balance")
async def get_balance(current_user: dict = Depends(get_current_user)):
    return {"balance": current_user.get("balance", 100000000)}

@router.post("/balance/update")
async def update_balance(amount: float, current_user: dict = Depends(get_current_user)):
    try:
        supabase.table("users").update({"balance": amount}).eq("id", current_user["id"]).execute()
        return {"message": "Balance updated", "new_balance": amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
