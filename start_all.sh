#!/bin/bash

# Pastikan berada di root project
PROJECT_ROOT=$(pwd)

echo "🚀 Memulai Ekosistem Stock Scanner CTG (3-Worker Optimized)..."

# Kill ghost processes if any
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "run_scanner.py" 2>/dev/null
pkill -f "update_market_data.py" 2>/dev/null
pkill -f "sync_universe.py" 2>/dev/null
pkill -f "db_janitor.py" 2>/dev/null

# Cleanup local cache files
rm -rf "$PROJECT_ROOT/data/cache/"*.parquet
rm -rf "$PROJECT_ROOT/apps/backend/data/cache/"*.parquet

# Load Virtual Environment
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT/apps/backend

# 1. Validasi & Migrasi Database
echo "🔍 [1/5] Memeriksa & Menyiapkan Tabel Database (Supabase)..."
python3 scripts/check_tables.py
if [ $? -ne 0 ]; then
    echo "❌ Gagal menyiapkan database. Periksa koneksi Supabase Anda."
    exit 1
fi

# 2. WORKER 1: Discovery (Latar Belakang)
echo "📊 [2/5] Worker 1: Discovery IDX Active (Latar Belakang)..."
python3 scripts/sync_universe.py &
WORKER1_PID=$!

# 3. WORKER 2: Real-time Price Update
echo "⚡ [3/5] Worker 2: Real-time Price Updater (Polling)..."
python3 scripts/update_market_data.py &
WORKER2_PID=$!

# 4. WORKER 3: DB Janitor (Maintenance)
echo "🧹 [4/5] Worker 3: Database Janitor (Auto-clean)..."
python3 scripts/db_janitor.py &
WORKER3_PID=$!

# 5. Jalankan Backend & Frontend
echo "🔌 [5/5] Menyalakan Backend API & Frontend UI..."

# Backend
cd apps/backend
PYTHONUNBUFFERED=1 PYTHONPATH=. uvicorn app.main:app --port 8000 --host 0.0.0.0 --log-level info &
BACKEND_PID=$!

# Frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Jalankan Scanner Strategi CTG
cd $PROJECT_ROOT
(
    while true; do
        echo "--- SCAN START: $(date) ---"
        python3 scripts/run_scanner.py
        echo "--- SCAN END: Menunggu 15 Menit ---"
        sleep 900
    done
) &
SCANNER_PID=$!

echo "-------------------------------------------------------"
echo "🌟 SEMUA SISTEM AKTIF DENGAN 3 WORKER PARALEL!"
echo "📈 Dashboard: http://localhost:3000"
echo "🛠️  Backend  : http://localhost:8000"
echo "💡 Log ditampilkan langsung di terminal ini."
echo "-------------------------------------------------------"

cleanup() {
    echo -e "\n🛑 Menghentikan semua layanan & worker..."
    kill $WORKER1_PID $WORKER2_PID $WORKER3_PID $BACKEND_PID $FRONTEND_PID $SCANNER_PID 2>/dev/null
    echo "👋 Sampai jumpa!"
    exit
}

trap cleanup SIGINT
wait
