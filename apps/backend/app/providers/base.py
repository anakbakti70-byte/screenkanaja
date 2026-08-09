from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime

class BaseDataProvider(ABC):
    @abstractmethod
    def get_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start: datetime = None, 
        end: datetime = None,
        limit: int = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a given symbol and timeframe.
        Returns a pandas DataFrame with columns: Open, High, Low, Close, Volume.
        Index should be Datetime.
        """
        pass

    @abstractmethod
    def get_last_price(self, symbol: str) -> float:
        """
        Get the most recent price for a symbol.
        """
        pass
