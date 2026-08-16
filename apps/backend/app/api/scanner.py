from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.scanner.scanner_core import ScannerEngine
from app.core.database import supabase

router = APIRouter()
engine = ScannerEngine()

@router.get("/status")
async def get_status():
    return {"status": "idle"}

@router.post("/run")
async def run_scanner(market: str = "idx", timeframe: str = "1d"):
    """
    Trigger a manual scan for a specific market and timeframe.
    """
    try:
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
    """
    Fetch scan results. If latest_only is True, returns only the most recent result per symbol/method.
    """
    try:
        if latest_only:
            # Optimal query: filter in DB as much as possible
            query = supabase.table("divergence_signal").select("*")
            if market: query = query.eq("market", market.lower())
            if timeframe: query = query.eq("timeframe", timeframe)
            
            # We still need some local logic to get the ABSOLUTE latest per symbol/method
            # unless we use a complex RPC, which we want to avoid for now.
            response = query.order("created_at", desc=True).limit(200).execute()
            data = response.data
            
            unique_results = {}
            for item in data:
                # Key based on symbol, method and timeframe
                key = f"{item['symbol']}_{item['method']}_{item['timeframe']}"
                if key not in unique_results:
                    unique_results[key] = item
            
            final_data = list(unique_results.values())
            if sort_by == "score":
                final_data.sort(key=lambda x: x['score'] or 0, reverse=True)
            
            return final_data[:limit]

        order_col = "score" if sort_by == "score" else "created_at"
        query = supabase.table("divergence_signal").select("*").order(order_col, desc=True).limit(limit)
        
        if market:
            query = query.eq("market", market.lower())

        if symbol:
            query = query.eq("symbol", symbol.upper())
            
        if timeframe:
            query = query.eq("timeframe", timeframe)
            
        response = query.execute()
        return response.data
    except Exception as e:
        print(f"API ERROR (get_results): {e}")
        raise HTTPException(status_code=500, detail=str(e))
