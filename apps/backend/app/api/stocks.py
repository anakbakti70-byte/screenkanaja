from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.core.database import supabase

router = APIRouter()

@router.get("/ipo")
async def get_recent_ipos(limit: int = 5):
    """
    Fetches the most recent IPOs from the stocks table.
    """
    try:
        response = supabase.table("stocks") \
            .select("symbol, company_name, listing_date") \
            .not_.is_("listing_date", "null") \
            .order("listing_date", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_stocks(symbol: Optional[str] = None):
    try:
        # High limit to ensure we see all stocks in the universe
        query = supabase.table("stocks").select("*").order("symbol", desc=False)
        if symbol:
            query = query.ilike("symbol", f"%{symbol}%")
        
        response = query.limit(1000).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
