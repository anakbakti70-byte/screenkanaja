import requests
import logging
import pandas as pd
import io
import re
from typing import List, Dict, Any
from datetime import datetime

class IDXSource:
    """
    Handles fetching stock data from official IDX and dynamic mirrors.
    """
    def __init__(self):
        self.idx_url = "https://www.idx.co.id/primary/ListedCompany/GetStock?code=&sectionCode=&listBy=0&draw=1&start=0&length=1000"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }

    def fetch_all_stocks(self) -> List[Dict[str, Any]]:
        """
        Combines data from Official IDX API and dynamic mirror fallbacks.
        """
        all_stocks = {}

        # 1. Try Official IDX API (Listed Stocks)
        try:
            session = requests.Session()
            session.get("https://www.idx.co.id/id/data-pasar/data-saham/daftar-saham/", headers=self.headers, timeout=10)
            response = session.get(self.idx_url, headers=self.headers, timeout=20)
            if response.status_code == 200:
                data = response.json().get("data", [])
                for item in data:
                    symbol = item.get("Code", "").strip().upper()
                    if symbol:
                        all_stocks[symbol] = {
                            "symbol": symbol,
                            "company_name": item.get("Name", "").strip(),
                            "listing_date": self._parse_date(item.get("ListingDate"))
                        }
                if len(all_stocks) > 100:
                    logging.info(f"Discovered {len(all_stocks)} stocks from official IDX API.")
                    return list(all_stocks.values())
        except Exception as e:
            logging.warning(f"IDX API failed: {e}")

        # 2. Mirror Discovery
        mirrors = [
            "https://web-idn-ipo-data.netlify.app/data/stocks.json",
            "https://raw.githubusercontent.com/wildangunawan/Dataset-Saham-IDX/master/info.json"
        ]
        
        for url in mirrors:
            try:
                logging.info(f"Trying mirror: {url}")
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        if isinstance(data[0], str):
                            for sym in data:
                                if len(sym) >= 4:
                                    s_up = sym.strip().upper()
                                    all_stocks[s_up] = {"symbol": s_up, "company_name": f"{s_up} Tbk", "listing_date": None}
                        elif isinstance(data[0], dict):
                            for item in data:
                                sym = (item.get('Kode') or item.get('symbol') or item.get('ticker', '')).strip().upper()
                                if sym:
                                    all_stocks[sym] = {
                                        "symbol": sym,
                                        "company_name": item.get('Nama Perusahaan') or item.get('name', sym),
                                        "listing_date": self._parse_date(item.get('Tanggal Pencatatan') or item.get('listing_date'))
                                    }
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if len(k) == 4 and k.isupper():
                                name = v if isinstance(v, str) else v.get('name', k)
                                all_stocks[k] = {"symbol": k, "company_name": name, "listing_date": None}
                                
                    if len(all_stocks) > 100:
                        break
            except Exception as e:
                logging.warning(f"Mirror failed ({url}): {e}")

        # 3. E-IPO Scraping
        try:
            resp = requests.get("https://e-ipo.co.id/id/ipo/index", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                found = re.findall(r'([A-Z]{4})', resp.text)
                for t in found:
                    if t not in all_stocks and len(t) == 4:
                        all_stocks[t] = {"symbol": t, "company_name": f"{t} (E-IPO Upcoming)", "listing_date": None}
        except: pass

        return list(all_stocks.values())

    def _parse_date(self, date_str):
        if not date_str: return None
        try:
            d_str = str(date_str)
            if 'T' in d_str: return datetime.fromisoformat(d_str.replace('Z', '+00:00'))
            return datetime.strptime(d_str[:10], '%Y-%m-%d')
        except: return None
