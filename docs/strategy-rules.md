# Strategy Rules — Spesifikasi Implementasi

> Turunan teknis dari `trading-method.md`. Dokumen ini yang dipakai
> langsung untuk menulis kode di `app/market_structure/` dan
> `app/strategies/`. Setiap rule di sini harus punya unit test yang
> sesuai (lihat daftar di §7).

## 0. Prinsip Umum

1. Semua logika strategi **deterministic & rule-based** — tidak ada ML/AI
   di versi pertama.
2. Semua parameter (threshold, lookback period, dll) **harus dibaca dari
   `app/config/*.yaml`**, tidak boleh hardcoded di dalam kode strategi.
3. Setiap strategy class punya method `evaluate(ohlcv, indicators) ->
   SetupResult` yang mengembalikan status + skor komponen, bukan
   `True/False` mentah.
4. Tidak boleh mengganti definisi bullish vs hidden bullish divergence
   (lihat `trading-method.md` §2 dan §4).

## 1. Pivot / Swing Detection (`market_structure/pivots.py`, `swings.py`)

**Input:** OHLCV series.
**Output:** daftar swing high & swing low dengan index dan harga.

Metode: fractal/ZigZag berbasis threshold yang dikonfigurasi di
`config/pivot_thresholds.yaml`, contoh:

```yaml
pivot_detection:
  method: "atr_zigzag"      # atau "percent_zigzag"
  atr_period: 14
  atr_multiplier: 1.5       # swing baru harus bergerak >= 1.5x ATR
  min_bars_between_pivots: 3
```

Aturan:
- Swing high = titik lokal tertinggi yang diikuti pergerakan turun
  ≥ threshold sebelum swing high berikutnya.
- Swing low = kebalikannya.
- Ganti parameter ini lewat backtest, **bukan** lewat menebak di kode.

## 2. Major / Minor Movement (`market_structure/movements.py`)

**Status: `[BUTUH KALIBRASI]`** — ini bagian paling sensitif di seluruh
proyek karena sumber aslinya adalah judgment visual, bukan rumus pasti.

Pendekatan awal yang disarankan:

1. Ambil semua swing point dari §1.
2. **Major movement** = swing-to-swing yang magnitudonya berada di top-N
   percentile dari semua pergerakan dalam lookback window (parameter
   `major_percentile`, default 70).
3. **Minor movement** = sisanya, dinested di dalam major movement.
4. Cari **penurunan paling panjang** dalam window sebagai kandidat
   gerakan ke-3, lalu bangun 5 gerakan (movement 1-5) di sekitarnya
   sesuai urutan swing high/low yang berselang-seling.
5. Jangan finalisasi threshold ini tanpa membandingkan output algoritma
   dengan minimal 10-15 contoh chart yang kamu tandai manual sebagai
   "ini gerakan ke berapa" (ground truth dataset kecil).

Output: setiap candle diberi label `movement_number` (1-5) dan
`movement_type` (major/minor).

## 3. Bullish Divergence (`strategies/bullish_divergence.py`)

**Syarat (semua harus benar):**

```
1. Trend saat ini = downtrend (lihat market_structure/trend.py)
2. Movement label = gerakan ke-5 (dari §2)
3. Price membuat Lower Low dibanding swing low sebelumnya
4. Minimal 1 dari {RSI, MACD, AO} membuat Higher Low pada titik yang sama
5. Candle confirmation belum wajib di tahap ini (masuk ke §5)
```

**Double bullish divergence** (`strategies/double_bullish.py`): sama
seperti di atas, tapi kondisi lower-low/higher-low terjadi dua kali
berturut-turut sebelum konfirmasi — pattern class terpisah, reuse logic
dari `bullish_divergence.py` lewat inheritance/composition, jangan
duplikasi kode swing detection.

## 4. Correction (`strategies/correction.py`)

**Prasyarat:** ada bullish divergence sebelumnya yang sudah mencapai TP
(lihat riwayat setup di database, bukan re-deteksi dari nol).

**Syarat:**

```
1. Setup bullish divergence sebelumnya berstatus TP_HIT
2. Tarik Fibonacci retracement dari swing LOW (sebelum naik) ke
   swing HIGH (titik TP)
3. Price saat ini berada di dalam correction zone
   (default: 0.382 - 0.618, dikonfigurasi di pivot_thresholds.yaml
   atau file config terpisah `fibonacci.yaml`)
4. Cek timeframe lebih kecil: apakah ada bullish divergence di sana?
5. Jika ya → status WAIT FOR CANDLE CONFIRMATION
```

Fibonacci **tidak pernah** dipakai sebagai sinyal entry berdiri sendiri —
selalu dikombinasikan dengan syarat #4.

## 5. Hidden Bullish Divergence (`strategies/hidden_bullish.py`)

**Syarat:**

```
1. Trend saat ini = uptrend
2. [MANUAL FLAG] Pattern (triangle/continuous) — untuk MVP, field ini
   diisi TRUE/FALSE oleh user di UI (chart detail), bukan dideteksi
   otomatis. Simpan sebagai bagian dari SetupResult, bukan silently
   diabaikan.
3. Struktur 5 gerakan diberi label A-B-C-D-E
4. Price membuat Higher Low
5. Indicator (RSI/MACD/AO) membuat Lower Low pada titik yang sama
```

Kondisi "hidden gagal" (disebut di transkrip) = ketika syarat #4-5
terpenuhi tapi price gagal lanjut naik dan menembus invalidation →
status berubah ke `INVALIDATED`, dicatat terpisah untuk analitik nanti
(apakah hidden bullish tanpa pattern valid lebih sering gagal — bisa
dicek lewat backtest).

## 6. Candle Confirmation (`confirmation/candle.py`)

```
1. Candle HARUS sudah closed (candle timestamp + timeframe duration <= now)
2. Candle harus bullish (close > open)
3. Body candle >= X% dari range candle (default 50%, dari config) —
   supaya tidak lolos candle doji/wick panjang
4. Optional: hammer/pinbar/marubozu sebagai variasi confirmation
   (confirmation/hammer.py, pinbar.py, marubozu.py) — tidak wajib,
   tapi kalau match, boleh menambah nilai pada scoring
```

## 7. Risk / Invalidation (`risk/`)

```
Invalidation = titik yang jika ditembus, struktur setup batal
              (biasanya swing low yang membentuk divergence)
Stop Loss    = invalidation ± buffer kecil (dikonfigurasi, default 0%)
Take Profit  = Fibonacci extension level terdekat (untuk correction)
               atau swing high sebelumnya (untuk bullish divergence biasa)
Risk %       = (Entry - SL) / Entry
Reward %     = (TP - Entry) / Entry
R:R          = Reward % / Risk %
```

Jangan menolak setup hanya karena R:R < 1:4 — itu bukan aturan wajib dari
transkrip (lihat `trading-method.md` §6), tapi tampilkan R:R sebagai info
supaya user yang memutuskan.

## 8. Status Lifecycle

```
WATCH → APPROACHING → SETUP DETECTED → WAIT CONFIRMATION
      → READY → (TP HIT | INVALIDATED)
```

Transisi status harus dicatat dengan timestamp (untuk keperluan §9 dan
backtesting) — jangan overwrite status lama, simpan histori.

## 9. Scoring System (Software feature — bukan dari transkrip)

Formula awal (bobot di `config/scoring_weights.yaml`, jangan hardcode):

```
score = w1*major_trend_match + w2*five_movement_match
      + w3*divergence_match + w4*indicator_confirmation
      + w5*fibonacci_zone_match + w6*lower_tf_confirmation
      + w7*candle_confirmation + w8*risk_reward_quality
```

**Wajib:** setelah backtest engine jalan (lihat `architecture.md`),
validasi apakah score tinggi berkorelasi dengan win rate lebih baik.
Kalau tidak, revisi bobot berdasarkan data — jangan biarkan bobot ini
jadi angka estetika semata.

## 10. Daftar Unit Test Wajib

```
test_pivot_detection()
test_major_minor_classification()
test_five_movement_sequence()
test_regular_bullish_divergence()
test_double_bullish_divergence()
test_hidden_bullish_divergence()
test_correction_fibonacci_zone()
test_fibonacci_extension_targets()
test_candle_confirmation_rejects_unclosed_candle()
test_candle_confirmation_rejects_small_body()
test_risk_reward_calculation()
test_status_transition_history()
test_scoring_weights_configurable()
```

## 11. Constraints (Wajib Dipatuhi Siapapun yang Coding)

```
1. Jangan menambah aturan trading baru yang tidak ada di trading-method.md
2. Jangan ganti metode ini dengan technical analysis generik
3. Divergence sendirian != sinyal BUY
4. Tidak ada ML/AI di versi pertama
5. Jangan tampilkan output sebagai kepastian finansial
6. Candle yang belum close tidak boleh jadi confirmation
7. Fibonacci retracement = area koreksi, bukan sinyal entry tunggal
8. Semua logic strategy harus deterministic & testable
9. Setiap strategy wajib py unit test
10. Data provider harus di balik interface (lihat data-sources.md)
11. Backtest wajib jalan sebelum klaim strategi "bekerja"
12. Pisahkan jelas: setup terdeteksi vs confirmation vs entry vs
    invalidation vs TP vs SL
13. Jangan diam-diam mengganti definisi dari trading-method.md —
    kalau ada perubahan, update dokumen ini dulu
```