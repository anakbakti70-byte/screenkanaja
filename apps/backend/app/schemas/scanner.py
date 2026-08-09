from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ScannerResultSchema(BaseModel):
    symbol: str
    timeframe: str
    strategy_name: str
    status: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None
    score: float
    metadata: Dict[str, Any]
    timestamp: datetime

    class Config:
        from_attributes = True
