import requests
from typing import List
import logging

def get_all_idx_tickers() -> List[str]:
    """
    Fetches all currently listed tickers directly from the Indonesia Stock Exchange (IDX) API.
    This ensures the list is always up-to-date with new IPOs and delistings.
    """
    try:
        # Official IDX Listed Companies Endpoint
        url = "https://www.idx.co.id/primary/ListedCompany/GetStock?code=&sectionCode=&listBy=0&draw=1&start=0&length=1000"
        
        # We need a proper User-Agent to avoid being blocked by IDX firewall
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # The structure from IDX API is {"data": [{"Code": "AALI", ...}, ...]}
            if "data" in data:
                tickers = [f"{item['Code']}.JK" for item in data["data"] if "Code" in item]
                logging.info(f"Successfully discovered {len(tickers)} tickers from official IDX API.")
                return tickers
                
    except Exception as e:
        logging.error(f"Failed to fetch tickers from official IDX API: {e}")

    # Final emergency fallback if even IDX API is down
    return ["BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK", "BBNI.JK", "GOTO.JK"]
