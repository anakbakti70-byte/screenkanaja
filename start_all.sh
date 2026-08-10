#!/bin/bash

# Pastikan berada di root project
PROJECT_ROOT=$(pwd)

echo "🚀 Memulai Ekosistem Stock Scanner CTG..."

# Kill ghost processes if any
pkill -f "uvicorn app.main:app" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "run_scanner.py" 2>/dev/null

# Cleanup log files and local cache files
rm -f "$PROJECT_ROOT/backend.log" "$PROJECT_ROOT/frontend.log"
rm -rf "$PROJECT_ROOT/data/cache/"*.parquet
rm -rf "$PROJECT_ROOT/apps/backend/data/cache/"*.parquet
touch "$PROJECT_ROOT/backend.log" "$PROJECT_ROOT/frontend.log"

# Load Virtual Environment
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PROJECT_ROOT/apps/backend

# 1. Validasi & Migrasi Database (Otomatis Membuat Tabel Cache jika belum ada)
echo "🔍 [1/4] Memeriksa & Menyiapkan Tabel Database (Supabase)..."
python3 scripts/check_tables.py
if [ $? -ne 0 ]; then
    echo "❌ Gagal menyiapkan database. Periksa koneksi Supabase Anda."
    exit 1
fi

# 2. Sinkronisasi Data Master (Initial Sync)
echo "📊 [2/4] Sinkronisasi Data Saham IDX (Latar Belakang)..."
python3 scripts/sync_universe.py &
SYNC_PID=$!

# 3. Jalankan Backend & Frontend secara Paralel
echo "🔌 [3/4] Menyalakan Backend API & Frontend UI..."

# Backend - Unbuffered for real-time logging
cd apps/backend
PYTHONUNBUFFERED=1 PYTHONPATH=. uvicorn app.main:app --port 8000 --host 0.0.0.0 --log-level info >> "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "   ✅ Backend berjalan di port 8000 (Log: backend.log)"

# Frontend - Force clean install if needed and run
cd ../frontend
echo "   📦 Verifikasi dependensi frontend..."
npm install >> "$PROJECT_ROOT/frontend.log" 2>&1
rm -rf node_modules/.vite
npm run dev >> "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "   ✅ Frontend berjalan di port 3000 (Log: frontend.log)"

# 4. Jalankan Scanner Strategi CTG
echo "🔍 [4/4] Mengaktifkan Auto-Scanner Strategi Divergence..."
cd $PROJECT_ROOT
(
    while true; do
        echo "--- SCAN START: $(date) ---"
        python3 scripts/run_scanner.py
        echo "--- SCAN END: Menunggu 15 Menit ---"
        sleep 900
    done
) >> "$PROJECT_ROOT/backend.log" 2>&1 &
SCANNER_PID=$!

echo "-------------------------------------------------------"
echo "🌟 SEMUA SISTEM AKTIF!"
echo "📈 Akses Dashboard: http://localhost:3000"
echo "🛠️  Backend API   : http://localhost:8000"
echo "💡 Tekan Ctrl+C untuk mematikan semua layanan sekaligus."
echo "-------------------------------------------------------"

cleanup() {
    echo -e "\n🛑 Menghentikan semua layanan..."
    kill $SYNC_PID $BACKEND_PID $FRONTEND_PID $SCANNER_PID 2>/dev/null
    echo "👋 Sampai jumpa!"
    exit
}

trap cleanup SIGINT
wait
