from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.core.database import supabase

from app.providers.yfinance_provider import YFinanceProvider

router = APIRouter()
provider = YFinanceProvider()

@router.get("/{symbol}/candles")
async def get_stock_candles(symbol: str, timeframe: str = "1d"):
    try:
        provider_symbol = f"{symbol.upper()}.JK" if ".JK" not in symbol.upper() else symbol.upper()
        df = provider.get_ohlcv(provider_symbol, timeframe, limit=100)
        if df.empty:
            raise HTTPException(status_code=404, detail="Candles not found")

        # Convert to list of dicts for frontend
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        # Rename 'date' or 'datetime' to 'time'
        if 'date' in df.columns: df = df.rename(columns={'date': 'time'})
        if 'datetime' in df.columns: df = df.rename(columns={'datetime': 'time'})

        return df.to_dict(orient='records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ipo")
async def get_recent_ipos(limit: int = 5):
    """
    Fetches the most recent IPOs from the stock_master table.
    """
    try:
        response = supabase.table("stock_master") \
            .select("symbol, company_name, listing_date") \
            .lte("last_price", 1000) \
            .not_.is_("listing_date", "null") \
            .order("listing_date", desc=True) \
            .limit(limit) \
            .execute()
        return response.data
    except Exception as e:
        print(f"API ERROR (get_recent_ipos): {e}")
        # Return empty list instead of 500 if table is not ready
        return []

@router.get("/")
async def get_stocks(symbol: Optional[str] = None):
    try:
        # Filter: Price <= 1000 and Active
        query = supabase.table("stock_master").select("*").lte("last_price", 1000).eq("is_active", True).order("symbol", desc=False)
        if symbol:
            query = query.ilike("symbol", f"%{symbol}%")
        
        response = query.limit(1000).execute()
        return response.data
    except Exception as e:
        print(f"API ERROR (get_stocks): {e}")
        return []
