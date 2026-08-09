import requests
import pandas as pd
import io

def debug():
    url = "https://raw.githubusercontent.com/heru-setiawan/idx-stocks-list/master/idx_stocks.csv"
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        df = pd.read_csv(io.StringIO(resp.text))
        print("Columns:", df.columns.tolist())
        print("First 5 rows:\n", df.head())

if __name__ == "__main__":
    debug()
