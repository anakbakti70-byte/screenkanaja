from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone
from app.scanner.scanner_core import ScannerEngine
from app.core.database import supabase

router = APIRouter()

def get_engine():
    return ScannerEngine()

@router.get("/status")
async def get_status():
    return {"status": "idle"}

@router.post("/run")
async def run_scanner(market: str = "idx", timeframe: str = "1d"):
    try:
        engine = get_engine()
        results = await engine.run_scan(market, timeframe)
        return {
            "message": "Scan completed", 
            "count": len(results), 
            "market": market,
            "timeframe": timeframe
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results")
async def get_results(
    market: Optional[str] = Query(None), 
    symbol: Optional[str] = Query(None), 
    timeframe: Optional[str] = Query(None),
    limit: int = Query(50, gt=0, le=100),
    sort_by: str = "created_at",
    latest_only: bool = False
):
    try:
        query = supabase.table("divergence_signal").select("*") \
            .in_("status", ["READY", "VALID"])

        if market: query = query.eq("market", market.lower())
        if symbol: query = query.eq("symbol", symbol.upper())
        if timeframe: query = query.eq("timeframe", timeframe)

        order_col = "score" if sort_by == "score" else "created_at"
        response = query.order(order_col, desc=True).limit(200).execute()
        data = response.data

        if latest_only:
            unique_results = {}
            for item in data:
                key = f"{item['symbol']}_{item['method']}_{item['timeframe']}"
                if key not in unique_results:
                    unique_results[key] = item
            data = list(unique_results.values())

        # Sort by status priority: READY first, then VALID
        status_priority = {"READY": 0, "VALID": 1}
        data.sort(key=lambda x: status_priority.get(x.get('status', 'VALID'), 99))
        
        return data[:limit]
    except Exception as e:
        print(f"API ERROR (get_results): {e}")
        raise HTTPException(status_code=500, detail=str(e))
