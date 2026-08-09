import requests
import json

def test():
    urls = [
        "https://www.idx.co.id/primary/ListedCompany/GetStock?code=&sectionCode=&listBy=0&draw=1&start=0&length=1000",
        "https://raw.githubusercontent.com/viriyake/idx-stocks/master/idx_stocks.json",
        "https://raw.githubusercontent.com/ferryandika/idx-stock-list/master/idx_stock_list.csv"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for url in urls:
        try:
            print(f"Testing {url}...")
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"Success! Preview: {resp.text[:100]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test()
