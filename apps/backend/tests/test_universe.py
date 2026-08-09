import pytest
from unittest.mock import MagicMock, patch
from app.universe.source import IDXSource
from app.universe.service import UniverseService
from app.universe.sync import sync_universe

@pytest.fixture
def mock_idx_response():
    return {
        "data": [
            {"Code": "BBCA", "Name": "Bank Central Asia Tbk", "ListingDate": "2000-05-31T00:00:00"},
            {"Code": "BBRI", "Name": "Bank Rakyat Indonesia Tbk", "ListingDate": "2003-11-10T00:00:00"},
            {"Code": "NEWY", "Name": "New Stock Tbk", "ListingDate": "2024-01-01T00:00:00"}
        ]
    }

def test_parse_idx_response(mock_idx_response):
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = mock_idx_response
        mock_get.return_value.status_code = 200
        
        source = IDXSource()
        stocks = source.fetch_all_stocks()
        
        assert len(stocks) == 3
        assert stocks[0]['symbol'] == "BBCA"
        assert stocks[0]['company_name'] == "Bank Central Asia Tbk"

def test_to_provider_symbol():
    repo = MagicMock()
    service = UniverseService(repo)
    assert service.to_provider_symbol("BBCA") == "BBCA.JK"
    assert service.to_provider_symbol("AAPL", provider="us") == "AAPL"

@patch('app.universe.sync.UniverseRepository')
@patch('app.universe.sync.IDXSource')
def test_sync_logic(mock_source_cls, mock_repo_cls, mock_idx_response):
    # Setup mocks
    mock_source = mock_source_cls.return_value
    mock_repo = mock_repo_cls.return_value
    
    mock_source.fetch_all_stocks.return_value = [
        {"symbol": "BBCA", "company_name": "Bank Central Asia Tbk", "listing_date": None},
        {"symbol": "NEWY", "company_name": "New Stock Tbk", "listing_date": None}
    ]
    
    # Existing stocks in DB: BBCA (active), OLDY (active)
    mock_repo.get_all.return_value = [
        {"symbol": "BBCA", "company_name": "Bank Central Asia Tbk", "is_active": True},
        {"symbol": "OLDY", "company_name": "Old Stock Tbk", "is_active": True}
    ]
    
    sync_universe()
    
    # Verify:
    # 1. NEWY should be upserted (inserted)
    # 2. OLDY should be marked inactive
    # 3. BBCA should be ignored or unchanged (depending on name check)
    
    # Check upsert call
    args, kwargs = mock_repo.upsert_stocks.call_args
    upserted_symbols = [s['symbol'] for s in args[0]]
    assert "NEWY" in upserted_symbols
    
    # Check inactive call
    args, kwargs = mock_repo.mark_inactive.call_args
    assert "OLDY" in args[0]
