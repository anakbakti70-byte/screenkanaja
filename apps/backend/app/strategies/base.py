from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd

@dataclass
class SetupResult:
    status: str # DETECTED, VALID, STALE, INVALID, READY, WAITING_CONFIRMATION
    strategy_name: str
    symbol: str
    timeframe: str
    entry_price: Optional[float] = None
    entry_zone_low: Optional[float] = None
    entry_zone_high: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    tp_far: Optional[float] = None
    risk_reward: Optional[float] = None
    score: float = 0.0
    pattern_detected_at: Optional[pd.Timestamp] = None
    pattern_candle_index: Optional[int] = None
    entry_candle_index: Optional[int] = None
    signal_age: int = 0
    component_scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: pd.Timestamp = field(default_factory=pd.Timestamp.now)
    reason: str = ""

class BaseStrategy(ABC):
    def __init__(self, name: str, config: Optional[Dict] = None):
        self.name = name
        self.config = config or {}

    def get_max_age(self, timeframe: str) -> int:
        return 3 if timeframe == "1d" else 5

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        """
        Evaluates the strategy on the given data.
        Returns a SetupResult if a setup is found, otherwise None.
        """
        pass
