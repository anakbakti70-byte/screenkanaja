from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.backtesting.engine import BacktestEngineV4
from app.providers.yfinance_provider import YFinanceProvider
from app.core.database import supabase
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

@router.post("/run")
async def run_backtest(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    try:
        symbol = req.symbol.upper()
        # Ensure we always use .JK for yfinance to get realtime/latest data
        provider_symbol = f"{symbol}.JK" if ".JK" not in symbol else symbol

        # Force fetch from yfinance by ignoring cache to get realtime data
        print(f"DEBUG: Fetching latest REALTIME data for {provider_symbol}...")
        df = provider.get_ohlcv(provider_symbol, req.timeframe, limit=1000, use_cache=False)

        if df.empty or len(df) < 30:
            raise HTTPException(status_code=404, detail=f"Data historis tidak ditemukan atau terlalu sedikit untuk {symbol}")

        print(f"DEBUG: Running backtest for {symbol} on {len(df)} candles...")

        # Run Engine strictly following final.md
        engine = BacktestEngineV4(
            initial_balance=req.initial_capital,
            risk_per_trade_pct=req.risk_per_trade
        )

        # Override fees if provided
        from app.utils.market import Fees
        engine.fees = Fees(
            buy_pct=req.buy_fee,
            sell_pct=req.sell_fee,
            slippage_pct=req.slippage_pct
        )

        results = engine.run(df, symbol, req.timeframe)

        # Force key 'candles' for frontend compatibility
        if "history_candles" in results:
            results["candles"] = results.pop("history_candles")

        # Versioning marker
        results["engine_version"] = "V4.1.0-REALTIME"
        results["_debug_info"] = "BACKTEST_API_V4_FINAL"

        print(f"DEBUG: Backtest completed for {symbol}. Result keys: {list(results.keys())}")
        print(f"DEBUG: Candles count: {len(results.get('candles', []))}")

        return results
    except Exception as e:
        print(f"BACKTEST API ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
