#!/bin/bash

# Pastikan berada di root project
PROJECT_ROOT=$(pwd)

echo "🚀 Memulai Ekosistem Stock Scanner CTG (FULL AUTO-RELOAD)..."

# Nuclear cleanup function
nuclear_cleanup() {
    echo -e "\n🛑 Menghentikan SEMUA layanan..."
    # Matikan semua proses yang dijalankan oleh skrip ini
    pkill -P $$ 2>/dev/null
    # Matikan sisa-sisa proses jika ada
    pkill -f "uvicorn app.main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    pkill -f "watchfiles" 2>/dev/null
    pkill -f "run_scanner.py" 2>/dev/null
    pkill -f "update_market_data.py" 2>/dev/null
    pkill -f "sync_universe.py" 2>/dev/null
    pkill -f "db_janitor.py" 2>/dev/null
    echo "👋 Semua proses telah dimatikan secara bersih."
    exit 0
}

# Trap signals
trap nuclear_cleanup SIGINT SIGTERM EXIT

# 1. Bersihkan proses hantu di port utama
echo "🧹 Cleaning up ghost processes on ports 8000 & 3000..."
lsof -t -i:8000 | xargs kill -9 2>/dev/null
lsof -t -i:3000 | xargs kill -9 2>/dev/null

# 2. Load Virtual Environment
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT/apps/backend

# 3. Validasi Database
echo "🔍 [1/3] Memeriksa Database..."
python3 scripts/check_tables.py

# 4. Jalankan Workers dengan AUTO-RELOAD
# Menggunakan 'watchfiles' agar worker otomatis restart jika kode di folder app/ atau scripts/ berubah.
echo "📊 [2/3] Menyalakan Workers (Auto-Reload Enabled)..."

WATCH_PATHS="scripts apps/backend/app"

# Sync Universe (Harian)
watchfiles --filter python "python3 scripts/sync_universe.py" $WATCH_PATHS &
# Real-time Market Data Sync
watchfiles --filter python "python3 scripts/update_market_data.py" $WATCH_PATHS &
# DB Janitor (Maintenance)
watchfiles --filter python "python3 scripts/db_janitor.py" $WATCH_PATHS &
# ULTRA SCANNER (The Core Engine)
watchfiles --filter python "python3 scripts/run_scanner.py" $WATCH_PATHS &
# AUTO-PUSH to GitHub (Pushes changes automatically)
watchfiles "scripts/auto_push.sh" $WATCH_PATHS &

# 5. Jalankan Backend & Frontend
echo "🔌 [3/3] Menyalakan API & UI..."

# Backend API (Sudah ada --reload bawaan uvicorn)
cd apps/backend
PYTHONUNBUFFERED=1 PYTHONPATH=. uvicorn app.main:app --port 8000 --host 0.0.0.0 --log-level info --reload --reload-exclude "*.log" --reload-exclude "data/*" &

# Tunggu backend siap
echo "⏳ Menunggu API siap..."
MAX_ATTEMPTS=30
ATTEMPT=1
while ! curl -s --max-time 2 http://127.0.0.1:8000/api/health > /dev/null; do
  if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "⚠️ API lama merespon, tetap menjalankan frontend..."
    break
  fi
  echo -n "."
  sleep 1
  ((ATTEMPT++))
done
echo -e "\n✅ API Online!"

# Frontend UI
cd ../frontend
# Vite sudah mendukung Hot Module Replacement (HMR) secara native
npm run dev -- --port 3000 --host &

echo "-------------------------------------------------------"
echo "🌟 SISTEM AKTIF DENGAN FULL AUTO-RELOAD!"
echo "-------------------------------------------------------"
echo "Setiap perubahan pada file .py atau .tsx akan"
echo "langsung memperbarui sistem secara otomatis."
echo "-------------------------------------------------------"

wait
