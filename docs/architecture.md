# Architecture

## 1. Ringkasan

Web-based stock screening & trading setup scanner untuk IDX + US market,
berdasarkan metode di `trading-method.md`. Bukan auto-trading, bukan
sinyal jaminan profit — murni screening + ranking kandidat setup.

Stack:

```
Backend  : Python (FastAPI)
Frontend : React + TypeScript
Database : PostgreSQL
Data     : yfinance (polling, timeframe 15m ke atas)
Deploy   : Docker Compose (single monorepo)
```

## 2. Pipeline Utama

```
Market Data (yfinance)
     ↓
DataProvider (abstraksi + cache)
     ↓
OHLCV Engine
     ↓
   ┌─────────────┬─────────────────┐
   ▼             ▼
Indicators    Market Structure
(RSI/MACD/AO) (pivot/swing/movement)
   └─────────────┬─────────────────┘
                 ▼
         Strategy Engine
   (bullish div / double bullish /
    correction / hidden bullish)
                 ▼
         Fibonacci Engine
       (retracement / extension)
                 ▼
          Confirmation
        (candle close check)
                 ▼
           Risk Engine
       (entry/SL/TP/R:R)
                 ▼
       Scoring / Ranking
                 ▼
        ┌────────┴────────┐
        ▼                 ▼
   Backtesting         Web API
                           ▼
                    React Dashboard
```

Pipeline ini sama untuk **Morning Scanner** (dijalankan sebelum market
buka, full universe) dan **Live Scanner** (dijalankan berkala selama
market buka, hanya untuk kandidat yang sudah lolos morning scan +
watchlist).

## 3. Modul & Tanggung Jawab

| Modul | Tanggung jawab | Tidak boleh tahu tentang |
|---|---|---|
| `providers/` | Ambil OHLCV mentah | Strategi trading apapun |
| `indicators/` | Hitung RSI/MACD/AO | Sumber data (yfinance vs lainnya) |
| `market_structure/` | Swing, pivot, major/minor, 5 movement | Strategi spesifik (bullish/hidden) |
| `strategies/` | Terapkan rules dari `strategy-rules.md` | Cara data diambil, cara di-cache |
| `fibonacci/` | Retracement & extension murni matematis | Strategi mana yang memanggilnya |
| `confirmation/` | Cek candle close & body | Strategi, hanya terima OHLCV |
| `risk/` | Hitung entry/SL/TP/R:R | Scoring, UI |
| `scanner/` | Orkestrasi seluruh pipeline + ranking | Detail internal tiap modul |
| `backtesting/` | Simulasi historis pakai strategy yang sama persis dengan live | — |

Prinsip: **strategy engine tidak pernah tahu data berasal dari Yahoo
Finance.** Kalau provider diganti nanti, tidak ada satupun file di
`strategies/`, `market_structure/`, atau `risk/` yang perlu diubah.

## 4. Morning Scanner vs Live Scanner

**Morning Scanner** (dijalankan via `scanner/scheduler.py`, sebelum
market buka):

```
1. Ambil universe (config/universe.yaml)
2. Filter likuiditas (scanner/liquidity_filter.py)
3. Jalankan full pipeline untuk semua yang lolos filter
4. Simpan hasil + ranking ke DB
5. Dashboard tampilkan Top Setups
```

**Live Scanner** (polling berkala, interval mengikuti timeframe
terkecil yang dipakai — default tiap candle 15m/1H close):

```
1. Ambil daftar kandidat dari morning scan + watchlist
2. Fetch candle baru
3. Re-evaluate strategy utk kandidat itu saja (bukan full universe)
4. Update status (lihat status lifecycle di strategy-rules.md §8)
5. Simpan histori transisi status
```

Karena timeframe minimum 15m, **tidak perlu websocket/real-time
streaming** — polling terjadwal cukup dan jauh lebih sederhana untuk
dibangun & di-deploy.

## 5. Skalabilitas Scan Universe

Scan seluruh universe (ribuan ticker IDX+US) tiap pagi bisa berat kalau
tidak difilter. Urutan yang disarankan:

```
1. Liquidity filter (volume minimum, harga minimum) — paling murah, jalan duluan
2. Trend filter kasar (uptrend/downtrend dari MA sederhana) — murah
3. Baru jalankan market_structure + strategy engine (paling mahal)
```

Cache OHLCV di `data/cache/` (lihat `data-sources.md`) supaya tidak
fetch ulang candle yang sudah pernah diambil di hari yang sama.

## 6. Backtesting sebagai Modul Inti

Backtesting **tidak boleh** jadi fitur tempelan di akhir. Sejak strategy
pertama (`bullish_divergence.py`) selesai, langsung jalankan lewat
`backtesting/engine.py` yang memanggil **strategy class yang sama
persis** dengan yang dipakai scanner live — supaya tidak ada
"backtest logic" terpisah yang bisa drift dari logic live.

```
Historical OHLCV
     ↓
Replay candle per candle (walk-forward, bukan lookahead)
     ↓
Panggil strategy.evaluate() persis seperti live
     ↓
Simulasikan entry/SL/TP
     ↓
Hitung metrics: win rate, avg R:R, drawdown, profit factor, expectancy
```

## 7. Feedback Loop (Non-ML)

`feedback/` dan tabel `models/feedback.py` menyimpan kasus di mana user
menandai scanner salah (miss setup atau false positive). Data ini dipakai
manual untuk kalibrasi ulang `config/pivot_thresholds.yaml` dan
`config/scoring_weights.yaml` — bukan untuk training model ML.

## 8. Roadmap Implementasi

```
Phase 1  — Data: yfinance → OHLCV → PostgreSQL + cache
Phase 2  — Indicators: RSI, MACD, AO
Phase 3  — Market Structure: pivot → swing → major/minor → 5 movement
Phase 4  — Backtest harness minimal (dipakai mulai phase ini, bukan nanti)
Phase 5  — Strategy: Bullish Divergence → Double Bullish
Phase 6  — Strategy: Correction (+ Fibonacci retracement/extension)
Phase 7  — Strategy: Hidden Bullish (pattern = manual flag di MVP)
Phase 8  — Confirmation (candle close) + Risk Engine
Phase 9  — Scanner: liquidity filter → ranking → scoring
Phase 10 — Web API + React Dashboard
Phase 11 — Live Scanner (scheduler polling)
Phase 12 — Feedback loop + kalibrasi ulang parameter
```

Catatan: berbeda dari roadmap awal, **backtest masuk di Phase 4** (bukan
di akhir) supaya setiap strategy baru langsung tervalidasi begitu selesai
ditulis.