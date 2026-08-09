from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class StockUniverse:
    symbol: str
    company_name: str
    listing_date: Optional[datetime] = None
    is_active: bool = True
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
