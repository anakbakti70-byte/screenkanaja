import logging
import yfinance as yf
from datetime import datetime, timezone
from .source import IDXSource
from .repository import UniverseRepository
from .service import UniverseService

def sync_universe():
    logging.info("Starting Massive IDX Universe Sync & Yahoo Finance Enrichment...")
    
    source = IDXSource()
    repo = UniverseRepository()
    service = UniverseService(repo)
    
    # 1. Discovery Phase
    fetched_stocks = source.fetch_all_stocks()
    if not fetched_stocks:
        logging.error("Discovery failed. Sync aborted.")
        return

    # Ambil data yang sudah ada di DB untuk pengecekan
    existing_stocks_map = service.get_all_symbols_map()
    now = datetime.now(timezone.utc).isoformat()

    logging.info(f"Processing {len(fetched_stocks)} stocks. Updating existing or adding new...")
    
    # Template kunci standar untuk mencegah error PGRST102
    standard_keys = [
        "symbol", "company_name", "name", "listing_date",
        "shares_outstanding", "market_cap", "last_price", "board",
        "sector", "industry", "description", "is_active",
        "created_at", "updated_at", "last_synced_at"
    ]

    batch = []
    for i, stock in enumerate(fetched_stocks):
        symbol = stock['symbol']
        existing = existing_stocks_map.get(symbol)
        
        # Merge logic
        merged_stock = existing.copy() if existing else {k: None for k in standard_keys}
        merged_stock.update(stock)

        # Mapping 'name' for compatibility
        if 'company_name' in merged_stock:
            merged_stock['name'] = merged_stock['company_name']

        merged_stock.update({
            "is_active": True,
            "last_synced_at": now,
            "updated_at": now
        })
        if not existing:
            merged_stock["created_at"] = now

        # Enrichment (Yahoo Finance) - Only if sector is missing
        if not merged_stock.get('sector'):
            try:
                # Progress log every 10 stocks
                if i % 10 == 0: logging.info(f"Enriching {i}/{len(fetched_stocks)}: {symbol}")
                
                yf_ticker = yf.Ticker(f"{symbol}.JK")
                info = yf_ticker.info
                
                if info:
                    merged_stock.update({
                        "sector": info.get("sector"),
                        "industry": info.get("industry"),
                        "market_cap": info.get("marketCap"),
                        "last_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                        "shares_outstanding": info.get("sharesOutstanding"),
                        "description": info.get("longBusinessSummary"),
                        "company_name": info.get("longName") or merged_stock.get('company_name'),
                        "name": info.get("longName") or merged_stock.get('name')
                    })
            except Exception:
                pass

        # Pastikan hanya kunci standar yang dikirim dan semua kunci ada (meskipun None)
        final_stock = {k: merged_stock.get(k) for k in standard_keys}
        batch.append(final_stock)

        if len(batch) >= 50:
            repo.upsert_stocks(batch)
            batch = []

    if batch:
        repo.upsert_stocks(batch)

    logging.info(f"Sync completed. Upserted {len(fetched_stocks)} stocks.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_universe()
