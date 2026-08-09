from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.scanner.engine import ScannerEngine
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
        # Results are already SetupResult objects, which might need conversion to dict if not Pydantic
        # SetupResult is a dataclass, so we can use asdict or it might be serializable by FastAPI if we are lucky
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
    sort_by: str = "timestamp",
    latest_only: bool = False
):
    """
    Fetch scan results. If latest_only is True, returns only the most recent result per symbol.
    """
    try:
        if latest_only:
            # Simple approach: fetch more and filter in Python to ensure unique symbols
            # Better approach would be raw SQL with DISTINCT ON, but supabase-py is limited
            query = supabase.table("scanner_results").select("*").order("timestamp", desc=True).limit(500)
            if market: query = query.eq("market", market.lower())
            if timeframe: query = query.eq("timeframe", timeframe)
            
            response = query.execute()
            data = response.data
            
            unique_results = {}
            for item in data:
                # Normalize symbol (remove .JK if present) for deduplication
                base_symbol = item['symbol'].split('.')[0].upper()
                key = f"{base_symbol}_{item['timeframe']}"
                if key not in unique_results:
                    unique_results[key] = item
            
            final_data = list(unique_results.values())
            # Sort final data if needed
            if sort_by == "score":
                final_data.sort(key=lambda x: x['score'], reverse=True)
            
            return final_data[:limit]

        order_col = "score" if sort_by == "score" else "timestamp"
        query = supabase.table("scanner_results").select("*").order(order_col, desc=True).limit(limit)
        
        if market:
            query = query.eq("market", market.lower())
            
        if symbol:
            query = query.eq("symbol", symbol.upper())
            
        if timeframe:
            query = query.eq("timeframe", timeframe)
            
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
