from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Any
from app.backtesting.engine import BacktestEngineV4
from app.backtesting.virtual_broker import VirtualBroker
from app.providers.yfinance_provider import YFinanceProvider
from app.core.database import supabase
from app.scanner.scanner_core import is_idx_market_open
from app.core.market_utils import Fees
from .auth import get_current_user
import numpy as np
import math
from datetime import datetime, timezone

router = APIRouter()
provider = YFinanceProvider()

# --- MODELS ---

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    initial_capital: float = 1000000000000
    risk_per_trade: float = 1.0
    buy_fee: Optional[float] = 0.0019
    sell_fee: Optional[float] = 0.0029
    slippage_pct: Optional[float] = 0.001

class OrderRequest(BaseModel):
    session_id: int
    symbol: str
    side: str # BUY, SELL
    quantity: int
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class CreateSessionRequest(BaseModel):
    name: str
    initial_balance: float = 1000000000000

# --- HELPERS ---

def make_json_safe(data):
    if isinstance(data, dict): return {k: make_json_safe(v) for k, v in data.items()}
    elif isinstance(data, list): return [make_json_safe(v) for v in data]
    elif isinstance(data, (float, np.float64, np.float32)):
        if math.isnan(data) or np.isnan(data): return 0.0
        if math.isinf(data) or np.isinf(data): return "∞"
        return float(data)
    elif isinstance(data, (int, np.int64, np.int32, np.uint64, np.uint32)): return int(data)
    elif hasattr(data, 'isoformat'): return data.isoformat()
    return data

# --- SESSION ENDPOINTS ---

@router.get("/sessions")
async def get_sessions(current_user: dict = Depends(get_current_user)):
    res = supabase.table("backtest_sessions").select("*").eq("user_id", current_user["id"]).order("created_at", desc=True).execute()
    return res.data

@router.post("/sessions")
async def create_session(req: CreateSessionRequest, current_user: dict = Depends(get_current_user)):
    try:
        session = VirtualBroker.create_session(str(current_user["id"]), req.name, req.initial_balance)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: int, current_user: dict = Depends(get_current_user)):
    broker = VirtualBroker(session_id)
    broker.sync_positions_with_market()

    session = broker.get_session_info()
    if not session or str(session["user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")

    portfolio = broker.get_portfolio()

    total_market_value = 0
    for pos in portfolio:
        stock_res = supabase.table("stock_master").select("last_price").eq("symbol", pos["symbol"]).single().execute()
        last_price = float(stock_res.data["last_price"]) if stock_res.data and stock_res.data["last_price"] else float(pos["avg_price"])
        pos["current_price"] = last_price
        pos["market_value"] = pos["quantity"] * last_price
        pos["unrealized_pnl"] = (last_price - float(pos["avg_price"])) * pos["quantity"]
        pos["unrealized_pnl_pct"] = (((last_price / float(pos["avg_price"])) - 1) * 100) if float(pos["avg_price"]) > 0 else 0
        total_market_value += pos["market_value"]

    return make_json_safe({
        "session": session,
        "portfolio": portfolio,
        "total_market_value": total_market_value,
        "total_equity": float(session["current_balance"]) + total_market_value
    })

@router.post("/sessions/{session_id}/reset")
async def reset_session(session_id: int, current_user: dict = Depends(get_current_user)):
    broker = VirtualBroker(session_id)
    session = broker.get_session_info()
    if not session or str(session["user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")
    broker.reset_session()
    return {"message": "Session reset successfully"}

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, current_user: dict = Depends(get_current_user)):
    res = supabase.table("backtest_sessions").delete().eq("id", session_id).eq("user_id", current_user["id"]).execute()
    return {"message": "Session deleted"}

# --- TRADING ENDPOINTS ---

@router.post("/order")
async def place_order(req: OrderRequest, current_user: dict = Depends(get_current_user)):
    broker = VirtualBroker(req.session_id)
    session = broker.get_session_info()
    if not session or str(session["user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = broker.place_order(
            req.symbol, req.side, req.quantity, req.price,
            req.stop_loss, req.take_profit, source="MANUAL"
        )
        return make_json_safe(result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/transactions/{session_id}")
async def get_transactions(session_id: int, current_user: dict = Depends(get_current_user)):
    res = supabase.table("backtest_transactions").select("*").eq("session_id", session_id).order("ts", desc=True).execute()
    return make_json_safe(res.data)

@router.post("/sessions/{session_id}/run-strategy")
async def run_strategy_on_session(session_id: int, req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    broker = VirtualBroker(session_id)
    session = broker.get_session_info()
    if not session or str(session["user_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        symbol = req.symbol.upper()
        provider_symbol = f"{symbol}.JK" if ".JK" not in symbol else symbol
        df = provider.get_ohlcv(provider_symbol, req.timeframe, limit=1000, use_cache=False)
        if df.empty: raise HTTPException(status_code=404, detail=f"Data not found")

        engine = BacktestEngineV4(initial_balance=float(session["current_balance"]), risk_per_trade_pct=req.risk_per_trade)
        results = engine.run(df, symbol, req.timeframe)

        for trade in results.get("trades", []):
            broker.place_order(symbol, "BUY", trade["qty"], trade["entry_price"], source="STRATEGY")
            broker.place_order(symbol, "SELL", trade["qty"], trade["exit_price"], source="STRATEGY")

        return {"message": "Strategy backtest applied to session", "trade_count": len(results.get("trades", []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/symbols")
async def get_backtest_symbols(query: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    try:
        db_query = supabase.table("stock_master").select("symbol, company_name, last_price").eq("is_active", True)
        if query: db_query = db_query.ilike("symbol", f"%{query}%")
        response = db_query.order("symbol").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run")
async def run_strategy_backtest(req: BacktestRequest, current_user: dict = Depends(get_current_user)):
    try:
        symbol = req.symbol.upper()
        provider_symbol = f"{symbol}.JK" if ".JK" not in symbol else symbol
        df = provider.get_ohlcv(provider_symbol, req.timeframe, limit=1000, use_cache=False)
        if df.empty: raise HTTPException(status_code=404, detail=f"Data not found")

        engine = BacktestEngineV4(initial_balance=req.initial_capital, risk_per_trade_pct=req.risk_per_trade)
        engine.fees = Fees(buy_pct=req.buy_fee, sell_pct=req.sell_fee, slippage_pct=req.slippage_pct)
        results = engine.run(df, symbol, req.timeframe)

        if "history_candles" in results: results["candles"] = results.pop("history_candles")
        return make_json_safe(results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
