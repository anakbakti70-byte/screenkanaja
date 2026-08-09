# Trading Method — Sumber Kebenaran (Source of Truth)

> Dokumen ini merangkum metode trading dari materi/transkrip asli.
> **Aturan: siapa pun yang mengerjakan kode TIDAK BOLEH mengganti atau menambah
> definisi di sini tanpa konfirmasi ke pemilik metode.** Kalau ada bagian
> yang ambigu, tandai sebagai `[AMBIGU]` — jangan ditebak sendiri.

## 1. Tiga Kelompok Metode

Metode ini terdiri dari tiga kelompok utama:

1. **Bullish Divergence** (termasuk *double bullish divergence*)
2. **Correction** — kelanjutan dari bullish divergence setelah TP tercapai
3. **Hidden Bullish Divergence** (termasuk kondisi ketika hidden gagal)

Ketiganya dipakai di konteks tren yang berbeda:

| Metode | Konteks tren | Price | Indicator |
|---|---|---|---|
| Bullish Divergence | Downtrend | Lower Low | Higher Low |
| Hidden Bullish Divergence | Uptrend | Higher Low | Lower Low |
| Correction | Lanjutan uptrend setelah TP | — | — |

## 2. Bullish Divergence

**Definisi:** harga membuat *lower low*, sementara indikator membuat *higher low*.

Indikator yang dipakai: **RSI, MACD, AO (Awesome Oscillator)**.

Digunakan terutama saat harga dalam kondisi downtrend, dicari sebagai
potensi area akumulasi/reversal.

### Five Movement

Bullish divergence umumnya muncul setelah **gerakan kelima** dari sebuah
struktur pergerakan harga.

- **Major movement**: gerakan besar (struktur utama)
- **Minor movement**: gerakan kecil (di dalam major movement)

Pendekatan mencari bullish divergence: cari **penurunan paling panjang**
(biasanya diperlakukan sebagai gerakan ke-3), lalu gunakan struktur itu
untuk mengidentifikasi lima gerakan secara keseluruhan.

`[AMBIGU]` Batas pasti antara major vs minor movement bersifat visual/
judgment dari trader di transkrip — belum ada threshold numerik eksplisit.
Ini perlu diparameterisasi dan divalidasi lewat backtest (lihat
`strategy-rules.md` bagian 2).

### Multi-timeframe

Timeframe besar: **4H, Daily, Weekly** — dipakai untuk holding period
1 minggu s/d 1 bulan.

Timeframe kecil: **1m, 3m, 5m** — dipakai untuk day trading/scalping.
(Catatan implementasi: untuk versi aplikasi ini timeframe minimum yang
dipakai adalah **15m**, lihat `data-sources.md`.)

Prinsip: **semakin besar timeframe → jarak TP dan SL semakin jauh**;
semakin kecil timeframe → jarak TP dan SL semakin dekat.

Workflow major → minor:

```
Daily → deteksi major setup → ditemukan kandidat bullish divergence
     → turun ke timeframe lebih kecil (4H / 1H / 15m) → cari konfirmasi
```

## 3. Correction

Correction adalah metode lanjutan **setelah** bullish divergence sebelumnya
mencapai target (TP).

Alur konsep:

```
Bullish Divergence → Price naik → TP tercapai → Price correction
   → cari area correction (Fibonacci) → potential second entry
```

### Fibonacci Retracement

Ditarik dari **LOW ke HIGH** untuk mencari area correction.

Fibonacci **bukan sinyal entry tunggal**. Fungsinya menjawab pertanyaan:
*"Di mana saya harus menunggu harga melakukan koreksi?"*

Setelah harga masuk area Fibonacci correction, materi menjelaskan untuk
mengecek bullish divergence pada **timeframe yang lebih kecil**:

```
Price masuk Fibonacci Correction Zone
   → cek lower timeframe
   → ada bullish divergence? YES → potential entry
   → tunggu candle confirmation
```

### Fibonacci Extension

Dipakai untuk mencari target TP dalam metode correction (TP1, TP2, TP3).

## 4. Hidden Bullish Divergence

**Definisi:** harga membuat *higher low* (uptrend), sementara indikator
membuat *lower low*. Ini kebalikan dari regular bullish divergence dan
**tidak boleh ditukar definisinya**.

Berbeda dari regular bullish divergence, hidden bullish divergence
**harus didahului oleh sebuah pattern** (contoh yang disebut di materi:
triangle / continuous pattern).

Struktur gerakan pada hidden bullish diberi label **A-B-C-D-E** (lima
gerakan, dengan penamaan berbeda dari major/minor pada bullish divergence
biasa).

Alur:

```
Uptrend → Pattern (mis. triangle) → 5 movements (A-B-C-D-E)
   → Price Higher Low + Indicator Lower Low → Hidden Bullish Divergence
```

`[AMBIGU]` Definisi "pattern" (triangle/continuous pattern) di transkrip
dijelaskan lewat contoh visual, bukan aturan geometris presisi. Untuk versi
awal aplikasi, deteksi pattern ini **tidak dibuat otomatis** — cukup
tampilkan kondisi price/indicator yang terukur, dan pattern dikonfirmasi
manual oleh user di chart. Lihat `strategy-rules.md`.

## 5. Candle Confirmation ("Cendol")

Divergence/setup saja **tidak cukup** untuk entry. Perlu candle
confirmation setelah harga mencapai entry zone.

Aturan penting: **candle yang masih berjalan (belum close) tidak boleh
dipakai sebagai confirmation.** Tunggu candle close.

## 6. Risk Management

Setiap setup harus punya:

```
ENTRY → INVALIDATION → STOP LOSS → TAKE PROFIT
```

Invalidation adalah dasar pengelolaan risiko — sebelum entry, trader harus
mempertimbangkan apakah mampu menerima risiko sampai titik invalidation
tersebut.

Contoh perhitungan dari materi:

```
Entry = 1,000
SL    = 900   (Risk = 10%)
TP    = 1,400 (Reward = 40%)
R:R   = 1:4
```

R:R 1:4 disebut sebagai rasio yang menarik dalam konteks contoh tersebut
(bukan aturan baku minimum R:R — jangan hardcode 1:4 sebagai syarat wajib
tanpa validasi backtest).

## 7. Yang Bukan Bagian dari Metode (Perlu Ditegaskan)

Hal-hal berikut **eksplisit BUKAN** bagian dari transkrip asli — ini adalah
keputusan desain software dan harus diperlakukan terpisah:

- Scoring/ranking numerik (0-100) — lihat `strategy-rules.md` §6
- Status lifecycle (WATCH, APPROACHING, dst.) — representasi UI, bukan aturan trading
- Threshold numerik pasti untuk major/minor movement — perlu dikalibrasi

---

**Referensi silang:** aturan implementasi presisi ada di `strategy-rules.md`.
Dokumen ini adalah *definisi konsep*, bukan *spesifikasi algoritma*.