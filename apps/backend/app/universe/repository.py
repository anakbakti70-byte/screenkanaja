from typing import List, Dict, Any, Optional
from app.core.database import supabase
from .models import StockUniverse
from datetime import datetime

class UniverseRepository:
    def __init__(self):
        self.table = "stocks"

    def get_all(self) -> List[Dict[str, Any]]:
        """Fetch all stocks from Supabase."""
        response = supabase.table(self.table).select("*").execute()
        return response.data

    def get_active(self) -> List[Dict[str, Any]]:
        """Fetch only active stocks."""
        response = supabase.table(self.table).select("*").eq("is_active", True).execute()
        return response.data

    def upsert_stocks(self, stocks: List[Dict[str, Any]]):
        """UPSERT stocks into Supabase."""
        if not stocks:
            return
        
        # Supabase Python client uses 'upsert' which matches on primary key or unique constraints
        # Ticker (symbol) should be UNIQUE in the DB.
        try:
            supabase.table(self.table).upsert(stocks, on_conflict="symbol").execute()
        except Exception as e:
            print(f"Error during upsert: {e}")

    def mark_inactive(self, symbols: List[str]):
        """Mark stocks as inactive."""
        if not symbols:
            return
            
        try:
            # Update is_active=false for symbols in the list
            # Note: supabase-py doesn't support 'in' directly in update, so we might need a loop or raw sql
            # but we can use .in_ for filtering
            supabase.table(self.table).update({"is_active": False, "updated_at": datetime.utcnow().isoformat()}).in_("symbol", symbols).execute()
        except Exception as e:
            print(f"Error marking inactive stocks: {e}")
