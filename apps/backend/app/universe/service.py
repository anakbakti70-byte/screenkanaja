from typing import List, Dict, Any
from .repository import UniverseRepository
from .models import StockUniverse

class UniverseService:
    def __init__(self, repository: UniverseRepository):
        self.repo = repository

    def get_active_stocks(self) -> List[StockUniverse]:
        """Returns a list of active StockUniverse objects."""
        data = self.repo.get_active()
        return [
            StockUniverse(
                symbol=item['symbol'],
                company_name=item['company_name'],
                listing_date=item.get('listing_date'),
                is_active=item['is_active'],
                last_synced_at=item.get('last_synced_at')
            ) for item in data
        ]

    def to_provider_symbol(self, symbol: str, provider: str = "yfinance") -> str:
        """Normalizes symbol for specific providers."""
        if provider == "yfinance":
            return f"{symbol}.JK"
        return symbol

    def get_all_symbols_map(self) -> Dict[str, Dict[str, Any]]:
        """Returns a map of symbol -> stock data for easy comparison."""
        data = self.repo.get_all()
        return {item['symbol']: item for item in data}
