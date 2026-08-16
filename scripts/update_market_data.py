import os
import sys
import time
import yfinance as yf
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Add apps/backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'backend'))

from app.core.database import supabase
from app.utils.market import is_idx_market_open

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "apps" / "backend" / ".env")

def update_realtime_data():
    """
    Worker 2: Update harga real-time hanya untuk emiten yang SUDAH ADA di database.
    """
    # Rule: Only run during IDX Market Hours (08:45-12:00, 12:24-17:00 WIB)
    if not is_idx_market_open():
        print(f"😴 [Worker 2] Market is CLOSED. Skipping update at {datetime.now()}.")
        return

    print(f"🔄 [Worker 2] Starting Real-time Price Update (Market Open): {datetime.now()}")

    try:
        # 1. Ambil HANYA emiten yang sudah terdaftar di database (stock_master)
        # Kita filter yang aktif agar lebih efisien
        res = supabase.table("stock_master").select("symbol").eq("is_active", True).execute()
        db_stocks = res.data

        if not db_stocks:
            print("⚠️ Tidak ada data emiten di database. Pastikan Worker 1 (Discovery) sudah berjalan.")
            return

        symbols = [s['symbol'] for s in db_stocks]
        # Format untuk yfinance (tambah .JK)
        yf_symbols = [f"{s}.JK" for s in symbols]

        print(f"📈 Mengupdate {len(symbols)} emiten yang ada di database...")

        # 2. Download data terbaru secara massal (Batch Download)
        # yfinance.download jauh lebih cepat daripada memanggil Ticker satu per satu
        data = yf.download(
            tickers=yf_symbols,
            period="1d",
            interval="1m", # Ambil interval terkecil untuk harga paling fresh
            group_by='ticker',
            auto_adjust=True,
            prepost=True,
            threads=True, # Gunakan multi-threading
            progress=False
        )

        updates_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        # 3. Proses hasil download dan update ke Supabase
        for symbol in symbols:
            try:
                yf_sym = f"{symbol}.JK"
                # Cek apakah data tersedia untuk simbol ini
                if yf_sym in data.columns.levels[0]:
                    ticker_data = data[yf_sym]
                    if not ticker_data.empty:
                        # Ambil harga closing terakhir
                        last_price = float(ticker_data['Close'].iloc[-1])

                        # Update ke database
                        supabase.table("stock_master").update({
                            "last_price": last_price,
                            "updated_at": now_iso
                        }).eq("symbol", symbol).execute()

                        updates_count += 1
            except Exception as e:
                # Lewati jika satu emiten gagal, lanjut ke yang lain
                continue

        print(f"✅ [Worker 2] Berhasil update {updates_count}/{len(symbols)} emiten.")
        print(f"🕒 Selesai pada {datetime.now()}")

    except Exception as e:
        print(f"❌ [Worker 2] Error fatal: {e}")

if __name__ == "__main__":
    # Jalankan terus menerus selama sistem aktif
    while True:
        update_realtime_data()
        # High-Speed 1s polling for stock master prices during market hours
        time.sleep(1)
