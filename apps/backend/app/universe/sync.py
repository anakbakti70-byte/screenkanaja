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

    existing_stocks_map = service.get_all_symbols_map()
    now = datetime.now(timezone.utc).isoformat()
    to_upsert = []
    
    # 2. Enrichment Phase (Yahoo Finance)
    # We only enrich NEW stocks or those missing sector info to be efficient
    logging.info(f"Processing {len(fetched_stocks)} stocks for enrichment...")
    
    for i, stock in enumerate(fetched_stocks):
        symbol = stock['symbol']
        existing = existing_stocks_map.get(symbol)
        
        # Determine if we need to fetch info from Yahoo
        # Fetch if: new stock OR sector is missing
        needs_enrichment = not existing or not existing.get('sector')
        
        if needs_enrichment:
            try:
                # Progress log every 10 stocks
                if i % 10 == 0: logging.info(f"Enriching {i}/{len(fetched_stocks)}: {symbol}")
                
                yf_ticker = yf.Ticker(f"{symbol}.JK")
                info = yf_ticker.info
                
                stock.update({
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "description": info.get("longBusinessSummary"),
                    "market_cap": info.get("marketCap"),
                    "company_name": info.get("longName") or stock['company_name']
                })
            except Exception as e:
                logging.warning(f"Failed to enrich {symbol} from Yahoo: {e}")

        stock.update({
            "is_active": True,
            "last_synced_at": now,
            "updated_at": now
        })
        if not existing:
            stock["created_at"] = now
            
        to_upsert.append(stock)

    # 3. Save to Supabase
    if to_upsert:
        # Batch upsert in chunks of 50 to avoid request size limits
        for i in range(0, len(to_upsert), 50):
            repo.upsert_stocks(to_upsert[i:i+50])

    logging.info(f"Sync completed. Upserted {len(to_upsert)} stocks with stable data.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sync_universe()
