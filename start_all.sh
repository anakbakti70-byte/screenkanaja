#!/bin/bash

# Pastikan berada di root project
PROJECT_ROOT=$(pwd)

echo "🚀 Memulai Ekosistem Stock Scanner CTG (Universal Auto-Reload)..."

# Nuclear cleanup function
nuclear_cleanup() {
    echo -e "\n🛑 Menghentikan SEMUA layanan (Nuclear Mode)..."
    # Kill specific PIDs if they exist
    kill $WORKER1_PID $WORKER2_PID $WORKER3_PID $SCANNER_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null

    # Force kill any remaining processes by pattern
    pkill -f "uvicorn app.main:app" 2>/dev/null
    pkill -f "vite" 2>/dev/null
    pkill -f "watchfiles" 2>/dev/null
    pkill -f "run_scanner.py" 2>/dev/null
    pkill -f "update_market_data.py" 2>/dev/null
    pkill -f "sync_universe.py" 2>/dev/null
    pkill -f "db_janitor.py" 2>/dev/null

    echo "👋 Semua proses telah dimatikan."
    exit 0
}

# Trap signals
trap nuclear_cleanup SIGINT SIGTERM EXIT

# 1. Kill ghost processes initially
pkill -f "uvicorn" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "watchfiles" 2>/dev/null

# 2. Cleanup Cache
rm -rf "$PROJECT_ROOT/data/cache/"*.parquet 2>/dev/null

# 3. Load Virtual Environment
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT/apps/backend

# 4. Validasi Database
echo "🔍 [1/3] Memeriksa Database..."
python3 scripts/check_tables.py

# 5. Jalankan Workers (Pantau Scripts + Logika Inti agar Rumus Baru Langsung Aktif)
echo "📊 [2/3] Menyalakan Workers & Scanner (Auto-Reload Enabled)..."

WATCH_PATHS="scripts/ apps/backend/app/"

watchfiles --filter python "python3 scripts/sync_universe.py" $WATCH_PATHS &
WORKER1_PID=$!
watchfiles --filter python "python3 scripts/update_market_data.py" $WATCH_PATHS &
WORKER2_PID=$!
watchfiles --filter python "python3 scripts/db_janitor.py" $WATCH_PATHS &
WORKER3_PID=$!
watchfiles --filter python "python3 scripts/run_scanner.py" $WATCH_PATHS &
SCANNER_PID=$!

# 6. Jalankan Backend & Frontend
echo "🔌 [3/3] Menyalakan API & UI..."

# Backend API
cd apps/backend
PYTHONUNBUFFERED=1 PYTHONPATH=. uvicorn app.main:app --port 8000 --host 0.0.0.0 --log-level info --reload &
BACKEND_PID=$!

# Frontend UI
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "-------------------------------------------------------"
echo "🌟 SEMUA SISTEM AKTIF DENGAN AUTO-UPDATE TOTAL!"
echo "✅ Edit RUMUS di: apps/backend/app/strategies/"
echo "✅ Edit API di  : apps/backend/app/api/"
echo "✅ Edit UI di   : apps/frontend/src/"
echo "✅ Edit SCRIPT di: scripts/"
echo "-------------------------------------------------------"
echo "💡 Tekan CTRL+C untuk mematikan SEMUA proses sekaligus."

# Wait for all background processes
wait
