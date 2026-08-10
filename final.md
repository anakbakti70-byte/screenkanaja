# Strategi Screener & Trading "Divergence Method" (CTG) — Saham IDX Harga < 1000

> Dokumen ini merangkum ulang materi tiga sesi kelas "SKS 12 — Divergence" (bullish divergence, double bullish divergence, correction, hidden bullish divergence) menjadi satu rulebook yang bisa dipakai untuk (a) inisialisasi database screener, (b) logika deteksi setup entry/SL/TP oleh sistem, dan (c) pembagian tugas antar model LLM yang tersedia di akun Groq/OpenRouter kamu.
>
> **Koreksi penting soal "akurasi >95%":** memilih model LLM tertentu (Qwen, Llama, GPT-OSS, dst) **tidak mengubah akurasi strategi trading ini**, berapa pun besar/kecil modelnya. Tidak ada model bahasa yang punya skor akurasi resmi untuk membaca chart/Fibonacci — itu klaim yang tidak eksis di dunia nyata, dari provider manapun. Yang benar-benar menentukan performa strategi:
> 1. **Kalkulasi Fibonacci, deteksi body candle/doji, level SL/TP** = matematika deterministik → wajib dihitung pakai **kode (Python/SQL)**, bukan ditebak oleh LLM (LLM sering meleset di angka presisi).
> 2. **Win-rate nyata** hanya bisa diketahui lewat **backtest data historis** — bukan dari model AI mana yang "membaca" datanya.
> 3. LLM di tabel §0 di bawah ini **hanya cocok untuk tugas berbasis bahasa/teks** (menjelaskan sinyal, meringkas alasan, klasifikasi kualitatif, generate kode) — bukan untuk "memvonis" apakah sinyal itu 95% akurat.
>
> Dokumen ini tetap saya lengkapi dengan pembagian tugas per model (§0) karena itu permintaan yang valid secara arsitektur sistem — tapi labelnya saya tulis jujur sebagai "kecocokan tugas", bukan "akurasi trading". Bukan nasihat keuangan.

---

## 0. Pembagian Model LLM per Tahap Pipeline (dari model yang tersedia di akunmu)

Prinsip pembagian: **tugas matematis/presisi → kode, bukan LLM**. LLM dipakai di tahap yang butuh bahasa, ringkasan, atau generate/validasi kode. Model dipilih berdasar kekuatan relatifnya (ukuran, reasoning, kecepatan, rate limit), bukan "akurasi trading".

| Tahap Pipeline | Tugas | Model Disarankan | Alasan Pemilihan | Fallback |
|---|---|---|---|---|
| **1. Ingest & Merge Data** (IDX + Netlify + GitHub + Yahoo) | Normalisasi field, dedup symbol, resolve konflik antar sumber | **Tidak perlu LLM** — pakai skrip Python/SQL murni (§1 & §7) | Ini kerja ETL deterministik, LLM cuma bikin lambat & mahal | — |
| **2. Filter Screener** (`price < 1000`, likuiditas, dsb) | Query filter dari DB | **Tidak perlu LLM** — SQL `WHERE` biasa (§1.3) | Sama, murni logika boolean | — |
| **3. Deteksi Pola & Kalkulasi Level** (5-wave, Fibonacci, SL/TP, candle body/doji) | Hitung angka presisi | **Tidak perlu LLM** — wajib kode (§7 pseudocode → implementasi Python asli, bukan LLM inference) | LLM manapun (termasuk GPT-OSS-120B) tidak reliable untuk aritmatika presisi berulang di ribuan baris data; delegasikan ke fungsi matematis | — |
| **4. Klasifikasi Cepat / Pra-saring Kualitatif** (mis. "apakah candle ini kelihatan seperti pola konsolidasi dari deskripsi teks/log", cek konsistensi label, triase volume tugas harian) | Klasifikasi teks ringan, throughput tinggi | **`llama-3.1-8b-instant`** | Paling cepat, limit harian besar (14.4K req/hari), cocok untuk proses ratusan emiten/hari tanpa habis kuota | `groq/compound-mini` |
| **5. Reasoning & Penjelasan Sinyal** (menjelaskan *kenapa* suatu emiten lolos filter divergence, menyusun narasi analisis ala §1–§6 dokumen ini, cross-check logika multi-timeframe) | Reasoning bahasa alami tingkat menengah–tinggi | **`llama-3.3-70b-versatile`** | Model reasoning terbesar yang tersedia di daftarmu (70B, production stage), cocok untuk sintesis penjelasan multi-langkah | **`qwen/qwen3.6-27b`** (jika butuh gaya jawaban berbeda) atau **`openai/gpt-oss-120b`** |
| **6. Generate/Review Kode Kalkulasi** (menulis/memperbaiki fungsi Fibonacci, validasi rumus SL/TP, generate query SQL screener) | Code generation & review | **`openai/gpt-oss-120b`** | Model terbesar berlabel *production*, umumnya kuat untuk tugas coding terstruktur | `llama-3.3-70b-versatile` |
| **7. Tugas Riset Tambahan / Tool-use** (browsing berita, cross-check compound info bila dibutuhkan konteks di luar DB) | Reasoning + tool orchestration | **`groq/compound`** | Didesain untuk tugas majemuk (compound), cocok jika pipeline butuh gabungan pencarian+reasoning | `groq/compound-mini` (kuota lebih hemat) |
| **8. Guardrail / Filter Konten Berbahaya** (mis. menyaring prompt-injection dari data eksternal sebelum masuk pipeline) | Safety classification | **`meta-llama/llama-prompt-guard-2-86m`** (lebih akurat) atau **`-22m`** (lebih cepat) | Model ini memang didesain khusus untuk deteksi prompt injection, bukan trading — tapi berguna kalau pipeline-mu menarik data teks dari sumber luar (berita, forum) | `openai/gpt-oss-safeguard-20b` untuk safety policy check yang lebih umum |
| **9. Transkripsi Audio** (kalau ada rekaman kelas/analisis suara lain yang perlu diproses ke teks) | Speech-to-text | **`whisper-large-v3-turbo`** | Lebih cepat dari versi non-turbo dengan kualitas setara untuk kebanyakan use-case | `whisper-large-v3` (kalau butuh akurasi transkrip maksimal, turbo sedikit trade-off akurasi demi kecepatan) |
| **10. Model Kecil untuk Task Volume Tinggi / Cadangan Darurat** | Apapun yang butuh throughput sangat tinggi & murah, atau saat model utama kena rate limit | **`openai/gpt-oss-20b`** | Ukuran lebih kecil dari 120B tapi tetap satu keluarga, bagus sebagai fallback cepat | `llama-3.1-8b-instant` |

**Catatan rate limit (dari data yang kamu kasih) — penting untuk desain pipeline harian:**
- `qwen/qwen3.6-27b`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `llama-3.3-70b-versatile` → **1.000 request/hari**. Kalau universe screener kamu ada >1.000 emiten dan tiap emiten butuh 1 call LLM, ini akan habis kuota. Solusi: LLM **hanya dipanggil untuk emiten yang SUDAH lolos filter matematis** (tahap 1–3, murni kode), bukan untuk semua emiten mentah.
- `llama-3.1-8b-instant` → 14.400 request/hari, jauh lebih longgar → cocok jadi lapisan pra-saring volume tinggi sebelum diteruskan ke model reasoning yang kuotanya lebih ketat.
- `groq/compound` & `compound-mini` → hanya 250 request/hari, dan `-27b`/`gpt-oss` model masih **preview/production** stage — jangan jadi satu-satunya tahap kritis pipeline harian, pakai sebagai pelengkap.

---

## 1. Skema Data Screener (Inisialisasi Database)

### 1.1 Sumber Data Fundamental/Listing (inisialisasi awal, gabung 3 sumber)

| Sumber | Field | Mapping ke field standar internal |
|---|---|---|
| **Official IDX** | Code, Name, ListingDate, Shares, ListingBoard, Sector, Industry | `symbol`, `name`, `listing_date`, `shares_outstanding`, `board`, `sector`, `industry` |
| **Netlify Mirror** | symbol, name, listing_date, category | dipakai sebagai *fallback/cross-check* utk `symbol`, `name`, `listing_date`; `category` → `board`/`sector` cadangan |
| **GitHub Dataset** | Kode, Nama Perusahaan, Tanggal Pencatatan, Papan Pencatatan | cross-check `symbol`, `name`, `listing_date`, `board` |

**Rule merge:** union by `symbol` (uppercase, trim). Jika ada konflik `listing_date`/`board` antar sumber → pakai Official IDX sebagai source of truth, dua sumber lain hanya untuk validasi/isi kekosongan (fallback chain: IDX → Netlify Mirror → GitHub Dataset).

### 1.2 Sumber Data Harga/Kuantitatif (Yahoo Finance) — dipakai untuk filter & kalkulasi indikator

Field yang **relevan langsung** untuk strategi ini (dari daftar lengkap yang kamu berikan):

- **Filter harga & likuiditas:** `currentPrice` / `regularMarketPrice`, `regularMarketDayHigh`, `regularMarketDayLow`, `regularMarketOpen`, `regularMarketPreviousClose`, `regularMarketVolume`, `averageDailyVolume10Day`, `averageDailyVolume3Month`, `averageVolume`, `averageVolume10days`, `bid`, `bidSize`, `ask`, `askSize`, `fiftyDayAverage`, `twoHundredDayAverage`, `fiftyTwoWeekHigh`, `fiftyTwoWeekLow`, `fiftyTwoWeekRange`, `regularMarketTime`, `marketState`, `exchange`, `fullExchangeName`, `exchangeTimezoneName`, `currency`, `symbol`, `shortName`, `longName`.
- **Konteks tambahan (opsional, tidak wajib untuk sinyal teknikal):** `marketCap`, `sector`, `sectorDisp`, `industry`, `beta`, `trailingPE`, `forwardPE`, `dividendYield`, dst. — field-field fundamental lain di daftarmu **tidak dipakai** oleh strategi ini karena strategi ini murni price-action + indikator momentum (lihat §2), bukan fundamental. Boleh disimpan di DB untuk keperluan lain, tapi jangan dijadikan syarat entry.

> Catatan penting dari transkrip: pembuat strategi ini **secara eksplisit tidak memakai volume/bandarmologi** sebagai basis sinyal ("saya enggak pernah pakai volume... volume itu tercipta kalau barang sudah naik... bisa dimanipulasi"). Jadi field volume boleh disimpan untuk keperluan likuiditas minimum saja (lihat §1.3), bukan sebagai indikator sinyal entry.

### 1.3 Filter Universe Screener (kriteria wajib)

```
WHERE currentPrice < 1000                         -- syarat permintaan: hanya saham < Rp1000
  AND exchange = 'JKT' (atau kode bursa IDX di Yahoo)
  AND regularMarketVolume >= threshold_likuiditas  -- rekomendasi transkrip: minimal setara ~5.000.000 lot/hari
                                                     -- ("bidover-nya enggak puluhan, enggak 2-3, minimal ya 5 juta")
  AND quoteType = 'EQUITY'
```

Catatan: nilai 5 juta lot adalah acuan kualitatif dari pengajar untuk saham "second liner yang masih liquid" — sesuaikan dengan realita data lo (bisa pakai rupiah value: `Close * regularMarketVolume` minimal sekian miliar/hari sebagai proxy lebih robust ketimbang lot mentah, karena harga di bawah 1000 bikin jumlah lot besar tidak selalu representasi likuiditas rupiah).

### 1.4 Sumber ide screening manual (dari transkrip, untuk dijadikan cron/menu tambahan)

1. **Top Gainer** (saat close market) → cari potensi *Hidden Bullish Divergence* (lanjutan uptrend).
2. **Top Loser** → cari potensi *Bullish Divergence* / *Double Bullish Divergence* (reversal dari downtrend).
3. **Candle Search** (fitur broker) → screening pola candle tertentu.
4. **Stock Universe pribadi** → user disarankan punya watchlist tetap per sektor (bukan lompat-lompat ke seluruh market tiap hari) supaya jam terbang di emiten tsb makin tinggi ("kalau tak kenal maka tak cuan").

---

## 2. Indikator yang Dipakai

Cukup **satu dari tiga** berikut yang confirm (tidak wajib ketiganya sinkron):

1. **RSI** (Relative Strength Index) — setting default.
2. **MACD** (Moving Average Convergence Divergence) — setting default.
3. **AO** (Awesome Oscillator) — setting default, ubah style dari histogram → **line** agar mudah dibaca. AO ≈ mirip MACD secara bentuk, jadi kalau AO sudah confirm, tidak perlu cek yang lain.

Urutan pengecekan yang disarankan pengajar: **AO dulu → kalau tidak ketemu, cek MACD → kalau tidak ketemu, cek RSI**. Cukup salah satu yang menunjukkan pola divergence, sudah dianggap valid (tidak perlu tiga-tiganya sepakat).

**Definisi divergence (dasar segalanya):**
- **Bullish (regular) divergence** = harga membentuk *lower low* (harga terus turun) TAPI indikator membentuk *higher low* (indikator naik). Ini adalah "mother of all" seluruh metode — semua metode turunannya (correction, hidden) tetap berpijak pada logika perbedaan harga vs indikator ini.
- **Hidden bullish divergence** = kebalikannya secara arah: harga bergerak **naik** (higher low pada fase koreksi dalam uptrend) namun indikator bergerak **turun**. Dipakai pada fase uptrend/continuation, bukan reversal.

---

## 3. METODE 1 — Bullish Divergence (Regular) & Double Bullish Divergence

### 3.1 Identifikasi Pola (wajib sebelum entry)

1. Cari **penurunan terpanjang** di price chart (biasanya ini adalah "gerakan/wave ke-3" dalam hitungan 5 wave turun — 1-2-3-4-5). Penurunan terpanjang = patokan utama untuk menentukan posisi wave saat ini.
2. Setelah wave-3 (penurunan terpanjang) teridentifikasi, cek apakah sudah terbentuk **5 kali gerakan turun** (mayor/besar dan/atau minor/kecil — keduanya valid, boleh ditarik dari time frame besar maupun kecil, hasilnya biasanya konvergen).
3. Preferensi pengajar: cari divergence pada **gerakan ke-5 (wave besar)**, karena di titik ini biasanya diferensiasi harga-vs-indikator paling jelas.

### 3.2 Rumus Titik Ancer-Ancer (Perkiraan) Area Bawah / Support Reversal

```
Fibonacci Retracement, ditarik dari LOW → HIGH sebelumnya
  (low penurunan terpanjang → high sebelum penurunan itu dimulai)
Level yang dipakai sebagai zona ancer-ancer: Fib 1.2 / 1.4 / 1.6
(catatan: skala Fibonacci extension gaya lokal, ekuivalen retracement >100%,
 fungsinya sebagai zona tunggu, BUKAN kepastian harga akan menyentuhnya)
```

Cara menarik: gunakan low & high dari **wick/ekor candle** (bukan body) — "tetap nyari dari low bawahnya tarik sampai atasnya", termasuk kalau ada shadow/wick, ekor paling bawah ke pucuk paling atas.

Fibo ini **hanya perkiraan area tunggu**, bukan syarat wajib harga harus menyentuhnya persis sebelum entry — syarat entry sesungguhnya ada di §3.3.

### 3.3 Syarat Konfirmasi Entry (WAJIB — tanpa ini dilarang entry)

Entry hanya boleh terjadi jika **SEMUA** syarat berikut terpenuhi bersamaan:

1. **Candle konfirmasi ("cendol")**: candle hijau yang **wajib berbadan (body)** — boleh bentuk marubozu/full body, hammer, atau pinbar (ada body signifikan). **Doji DILARANG untuk entry** (doji = pasar masih ragu, belum ada kepastian arah) → jika candle konfirmasi doji, WAJIB tunggu candle berikutnya.
2. **Indikator confirm**: minimal satu dari RSI/MACD/AO menunjukkan pola higher-low (bullish divergence) yang sinkron dengan harga.
3. **Candle konfirmasi harus CLOSE sesuai timeframe yang dipakai** (lihat §6 — aturan closing per timeframe). Entry dilakukan setelah candle tersebut close, bukan di tengah candle berjalan.
4. (Opsional, memperkuat) Ada area **support historis** di sekitar level tersebut sebagai confluence tambahan.

### 3.4 Stop Loss (Invalidation)

```
SL = Low dari candle konfirmasi ("cendol") itu sendiri
     (jika candle ada wick/ekor bawah → SL di ujung wick/ekor terbawah)
```

**Invalidasi pola (bukan cuma SL harga, tapi juga invalidasi struktur):** jika harga break/menembus turun melewati "kaki kiri" pola (titik low sebelum candle konfirmasi terbentuk), pola dianggap **fail/belum selesai** — bukan berarti market salah, tapi berarti wave belum selesai (bisa jadi baru masuk wave-3 padahal dikira wave-5). Sikapnya: **cut loss**, lalu tunggu pola baru terbentuk lebih ke bawah.

### 3.5 Take Profit

```
TP = Fibonacci Retracement, ditarik dari HIGH (wave-4, titik tertinggi
     sebelum leg turun terakhir) → LOW (low candle konfirmasi/cendol, wave-5)
Level target: Fib 0.5 / 0.6 / 0.7 (retracement) → minimal target di 0.6
```

- Target minimal yang disarankan pengajar: **Fib 0.6** (baru dianggap "TP wajar"), tapi TP boleh diambil lebih awal (0.5) maupun ditahan sampai 0.7 sesuai profil risiko masing-masing.
- **Boleh TP parsial** (sebagian lot) di level 0.5–0.6, sisanya biarkan lanjut jika ada potensi lanjutan (lihat Double Bullish Divergence di bawah).

### 3.6 Double Bullish Divergence (lanjutan jika Bullish Div gagal capai target)

**Kondisi terbentuknya:** setelah bullish divergence pertama terkonfirmasi, harga naik **TAPI TIDAK MENYENTUH target minimal 0.5**, lalu breakdown (turun lagi menembus low candle konfirmasi pertama).

**Syarat validitas Double Bullish Divergence:**
- Bullish divergence pertama & kedua **keduanya harus tetap valid** — artinya harga tidak boleh menembus ("break down") titik invalidasi (kaki kiri) dari pola pertama.
- Baru bisa entry pada bullish divergence kedua jika sudah ada candle konfirmasi (cendol) + indikator confirm lagi (sama seperti §3.3).

**Rumus SL Double Bullish Divergence:**
```
Cara mencari ancer-ancer bawah: Fibonacci retracement dari LOW candle
  konfirmasi pertama → HIGH (harga tertinggi yang tidak sempat tercapai) → 12/16
SL = di Fib "2" (level fib ke-2 dari skala fibo lokal 1-2-4-6-...)
     → alasan: jika harga break melewati Fib 2, biasanya ini indikasi
       indikator akan patah (invalid) dan struktur berubah jadi 5 wave baru
```

**Rumus TP Double Bullish Divergence — 2 target:**
```
TP Pendek = Fibonacci retracement dari HIGH (harga yang tak sempat
            tersentuh sebelumnya) → LOW candle konfirmasi kedua,
            target minimal di Fib 0.5–0.7 (sama seperti §3.5)

TP Jauh   = "hutang" dari target bullish divergence pertama yang belum
            tercapai. SYARAT WAJIB: harga harus break out melewati
            high/pick tertinggi sebelumnya dulu, baru boleh menarget
            level TP jauh ini. Jika tidak breakout → TP jauh batal,
            cukup ambil TP pendek saja.
```

Catatan penting (anti-FOMO / anti "sudah lewat"): **Double, Triple, Quadruple** — bullish divergence **HANYA bisa terjadi maksimal 2 kali (Double)**. Tidak ada Triple/Quadruple bullish divergence dalam struktur ini. Jika sudah gagal dua kali (harga breakdown dari kaki kiri pola kedua), maka setup ini dianggap **batal total** → **CUT LOSS wajib**, tunggu pola baru terbentuk dari titik yang lebih rendah (jangan dipaksakan average down tanpa batas).

### 3.7 Manajemen Posisi (Money Management)

- **DILARANG all-in.** Entry wajib bertahap/dicicil ("kita ngikutin tuan rumah punya hajat — tuan rumahnya aja nyicil, masa kita langsung gebak-gedeb").
- Jika mau **average up** setelah breakout dari Fib 1 (menuju TP jauh): tambahan lot **tidak boleh melebihi 50% dari lot awal**. Contoh: entry awal 1000 lot @580 → tambahan maksimal 500 lot, agar average price tidak naik terlalu jauh dari harga bawah.
- Prioritaskan manajemen risiko di atas ekspektasi profit ("prioritaskan resiko ketimbang profit").

---

## 4. METODE 2 — Correction (ABC)

Dipakai **setelah** Bullish Divergence (§3) sudah kena TP, sebagai entry kedua di titik koreksi (pullback) sebelum lanjut naik lagi.

### 4.1 Identifikasi & Syarat Setup

1. Setelah bullish divergence pertama kena TP (§3.5), harga biasanya mengalami **koreksi turun**.
2. Tandai fase ini sebagai gelombang **A-B-C** (bukan lagi 1-2-3-4-5): titik A = puncak setelah TP bullish div pertama, turun ke B, dst.
3. **Lebih valid** jika di zona koreksi tsb muncul lagi **bullish divergence di time frame kecil** sebagai confluence tambahan (opsional tapi sangat direkomendasikan — "another conviction").

### 4.2 Rumus Zona Tunggu Koreksi

```
Fibonacci Retracement dari LOW (bullish div pertama) → HIGH (titik TP
  bullish div pertama yang sudah kena)
Zona tunggu: Fib 0.6 / 0.7
```

### 4.3 Entry (dua varian, sesuai preferensi risk-reward)

**Varian A — Titik invalidasi ketat (SL dekat, RR lebih rendah):**
```
Entry = di zona Fib 0.6/0.7 setelah muncul candle konfirmasi (cendol)
        berbadan + indikator confirm (sama syarat §3.3)
SL    = low bullish divergence SEBELUMNYA (bukan cuma low candle konfirmasi)
```

**Varian B — Confluence penuh (SL lebih jauh, RR lebih besar, disukai pengajar):**
```
Syarat entry terbaik = bullish divergence pertama sudah kena TP
                        DAN koreksi mendekati titik invalidasi
                        DAN muncul bullish divergence lagi di zona koreksi
SL    = low invalidation dari pola bullish divergence di zona koreksi
```

### 4.4 Take Profit Correction

```
TP = Fibonacci Extension, dari LOW (bullish div pertama)
     → HIGH (titik TP bullish div pertama yang sudah kena)
     → diproyeksikan ke LOW correction (titik C)
Level Fibonacci Extension: 1.618 (dieja "162")
Syarat mencapai target: harga harus BREAK OUT dari high sebelumnya
  (titik TP bullish div pertama), minimal breakout Fib "1.2"
```

- Trade-off: metode Correction punya **SL paling jauh** (karena entry mepet ke titik invalidasi) dibanding metode lain, tapi **TP paling jauh** juga (risk & reward sama-sama terbesar dari 3 metode). Cocok untuk trader yang nyaman hold posisi lebih lama.

---

## 5. METODE 3 — Hidden Bullish Divergence (ABCDE)

Dipakai untuk fase **uptrend/continuation** (bukan reversal) — cocok untuk trader yang suka "beli saat naik, bukan saat bawah".

### 5.1 Syarat Wajib (2 syarat mutlak)

1. **Harus ada continuation pattern dulu** (bentuk konsolidasi): segitiga (symmetrical triangle / "sempa"), flag, pennant, dsb — pokoknya pola sideways/konsolidasi setelah kenaikan.
2. **Indikator harus berlawanan arah dengan harga (kebalikan dari regular divergence):** harga bergerak **naik** namun indikator bergerak **turun**.
3. Minimal ada **5 gerakan** di dalam pola konsolidasi tsb, dinamai **A-B-C-D-E** (ekuivalen 1-2-3-4-5 pada bullish divergence biasa, tapi konteksnya chart pattern/triangle).

### 5.2 Rumus Titik E (area entry)

```
Fibonacci Retracement dari LOW C → HIGH D
Level: Fib 0.6 / 0.7
```

### 5.3 Entry

```
Entry = setelah harga masuk zona Fib 0.6/0.7 (titik E) DAN muncul candle
        konfirmasi (cendol) berbadan DAN indikator confirm
SL    = LOW A (bukan low C, bukan low E — titik invalidasi tetap di low A)
```

### 5.4 Take Profit

```
TP = Fibonacci Retracement/Extension dari titik 0 (low A / dasar pola)
     → titik A, menggunakan skala Fibo "1" (breakout level) → "1.2"
Target minimal: Fib 1.2
Syarat wajib mencapai target: harga harus BREAK OUT melewati level "1"
  (level tertinggi sebelumnya / puncak pola D). Jika tidak breakout →
  berpotensi jadi "3=5" alias double top (gagal lanjut), maka TP dibatasi
  di area breakout terakhir yang sempat tercapai, atau CUT.
```

Catatan penting: karena entry sudah dilakukan **di bawah (di titik E)** sebelum breakout terjadi, trader **tidak perlu peduli** apakah breakout akhirnya terjadi persis sesuai plan — harga bawah sudah didapat lebih dulu, sehingga boleh TP parsial kapan saja sebelum breakout, dan sisanya menunggu breakout untuk target lanjutan.

### 5.5 Jika Hidden Bullish Divergence GAGAL (break down dari titik A)

```
Jika harga breakdown menembus low A → pola hidden dianggap invalid
Tindakan wajib: CUT LOSS (karena risiko sudah terlalu besar untuk ditahan)
Setelah cut loss, cari ulang pola BARU dari struktur yang berubah:
  pola lama yang tadinya A-B-C-D-E akan berubah jadi 5 wave turun baru
  (kembali ke logika §3 — regular bullish divergence) dengan invalidasi
  baru di puncak/pick TP bullish divergence sebelumnya
Rumus mencari titik bawah baru: Fibonacci retracement dari titik A → titik B
  menggunakan skala Fibo 1.2/1.6
```

---

## 6. Aturan Timeframe & Waktu Konfirmasi Candle (Anti "Sudah Lewat")

**Prinsip inti:** candle konfirmasi (cendol) HANYA sah setelah **CLOSE** sesuai timeframe entry yang dipakai. Entry di tengah candle berjalan (belum close) = melanggar SOP, rawan false signal, DILARANG.

| Timeframe | Waktu candle CLOSE (WIB, sesi bursa IDX 09:00–15:49/16:00) | Catatan |
|---|---|---|
| **1D (Daily)** | Saat **closing market** (≈15:49–16:00) | Acuan tertinggi untuk multi-timeframe validation |
| **4H** | Candle ke-2 dari jam buka, contoh: open 09:00 → close candle pertama sekitar jam 12:00-13:00 → candle konfirmasi ke-2 close **≈14:00** | Bergantung pembagian sesi bursa (candle 4H dimulai dari jam buka market, bukan jam 00:00 dunia) |
| **1H** | Setiap pergantian jam penuh: 09:00, 10:00, 11:00, 12:00, 13:00, 14:00, dst — tunggu candle jam berjalan close, baru entry | Kalau di jam tsb candle masih doji/merah, LANJUT tunggu candle jam berikutnya |
| **45 menit** | Ikuti pola yang sama: candle wajib close penuh sebelum entry (45m bukan pecahan sesi bursa standar IDX — pastikan platform charting sudah menyediakan resolusi ini, kalau tidak tersedia gunakan 30m atau 1H sebagai pengganti terdekat) | Sama-sama tunggu full close |
| **30 menit** | Tiap 30 menit dari jam buka: 09:00, 09:30, 10:00, dst | Sama-sama tunggu full close |

**Aturan Multi-Timeframe (MTF) — menentukan timeframe acuan bila sinyal muncul di banyak TF sekaligus:**
```
Jika bullish divergence / hidden terdeteksi di beberapa timeframe
  sekaligus (mis. muncul di 1H, 2H, 4H, dan Daily) →
  ACUAN = timeframe TERBESAR yang menunjukkan pola tsb (karena
  dianggap paling kuat/valid). Contoh: kalau ada di Daily, pakai Daily
  sebagai acuan konfirmasi entry (bukan 1H), meskipun itu berarti
  menunggu closing market yang lebih lama.
Semakin BESAR timeframe → semakin JAUH jarak TP dan jarak SL-nya.
Semakin KECIL timeframe → semakin DEKAT jarak TP dan jarak SL-nya.
```

**Panduan pemilihan timeframe berdasar gaya trading:**
- Swing/positional (hold berhari-hari s/d berminggu-minggu) → gunakan Daily atau 4H sebagai basis screening & konfirmasi.
- Day trading / scalping → gunakan timeframe kecil (1–5 menit, atau 30m/45m/1H sesuai permintaan) untuk konfirmasi entry, dengan tetap mengecek struktur wave dari TF lebih besar sebagai konteks (top-down analysis: identifikasi wave besar dulu di Daily/4H, baru cari entry presisi di TF kecil).

**Rule anti "dilarang entry karena sudah lewat" (FOMO guard) — checklist wajib sebelum entry:**
1. ❌ **Jangan entry jika target TP dari setup sebelumnya SUDAH tercapai** ("kalau misal sudah dari target jangan dikejar"). Tunggu setup baru terbentuk di bawah (koreksi/pattern baru), jangan mengejar harga yang sudah naik.
2. ❌ **Jangan entry tanpa candle konfirmasi (cendol) yang sudah CLOSE** sesuai timeframe (lihat tabel di atas) — entry preemptive di tengah candle = dilarang.
3. ❌ **Jangan entry pada candle doji** sebagai candle konfirmasi — tunggu candle berikutnya.
4. ❌ **Jangan buy on breakout semata** tanpa validasi struktur wave (khusus pola akumulasi/double bottom) — filosofi strategi ini justru: akumulasi di bawah bersama "bandar" sebelum breakout terjadi, bukan mengejar setelah breakout sudah kejadian, karena risk-reward jadi lebih buruk dan rawan false breakout.
5. ❌ **Jangan average up/nambah posisi melebihi 50% dari lot awal** (lihat §3.7).
6. ❌ **Jangan entry jika structure sudah invalid** (harga sudah menembus "kaki kiri" pola / low invalidation) — itu tandanya wave belum selesai, harus tunggu pola baru, bukan dipaksakan entry di pola lama.
7. ✅ Kalau ragu antar-indikator (mis. AO bilang divergence tapi RSI tidak) → **tetap valid selama SALAH SATU indikator confirm** (lihat §2), tidak perlu menunggu semua sepakat.

---

## 7. Ringkasan Formula (Quick Reference / Pseudocode)

```python
# ============ METODE 1: BULLISH DIVERGENCE (REGULAR) ============
def bullish_divergence(price, indicator):
    # 1. Deteksi 5 wave turun (low-terpanjang = wave-3 acuan)
    wave3_low = find_longest_decline(price)
    # 2. Confluence ancer-ancer bawah
    fib_zone = fibonacci_retracement(low=wave3_low, high=prior_high, levels=[1.2, 1.4, 1.6])
    # 3. Divergence check
    price_lower_low   = price.low[-1] < price.low[-2]
    indicator_higher_low = any(ind.low[-1] > ind.low[-2] for ind in [RSI, MACD, AO])
    is_divergence = price_lower_low and indicator_higher_low
    # 4. Candle konfirmasi
    confirm_candle = is_green(candle) and has_body(candle) and not is_doji(candle) and is_closed(candle, timeframe)
    if is_divergence and confirm_candle:
        entry = candle.close
        sl = candle.low
        tp = fibonacci_retracement(high=wave4_high, low=candle.low, levels=[0.5, 0.6, 0.7])  # target minimal 0.6
        return {"entry": entry, "sl": sl, "tp": tp}

# ============ DOUBLE BULLISH DIVERGENCE (jika TP pertama gagal 0.5) ============
def double_bullish_divergence(first_setup, price):
    if price.high_after_setup < first_setup.tp[0.5] and price.breaks_down(first_setup.entry_candle.low):
        second_confirm_candle = ...  # sama syarat seperti di atas
        if second_confirm_candle and not price.breaks(fib2_level):
            entry2 = second_confirm_candle.close
            sl2 = fib2_level  # invalidasi di Fibo level "2"
            tp_short = fibonacci_retracement(high=first_setup.untouched_high, low=second_confirm_candle.low, levels=[0.5,0.6,0.7])
            tp_far   = first_setup.tp  # hanya aktif JIKA breakout melewati high sebelumnya
            return {"entry": entry2, "sl": sl2, "tp_short": tp_short, "tp_far_conditional": tp_far}
    # jika double bullish divergence juga gagal (break down lagi) -> CUT LOSS, no triple/quad allowed

# ============ METODE 2: CORRECTION (ABC) ============
def correction(bullish_div_hit_tp):
    zone = fibonacci_retracement(low=bullish_div_hit_tp.entry_low, high=bullish_div_hit_tp.tp_price, levels=[0.6, 0.7])
    if price.in_zone(zone) and confirm_candle and (indicator_confirm or another_bullish_div_in_small_tf):
        entry = confirm_candle.close
        sl = min(bullish_div_hit_tp.entry_low, invalidation_point)  # SL lebih jauh dari metode 1
        tp = fibonacci_extension(low=bullish_div_hit_tp.entry_low, high=bullish_div_hit_tp.tp_price,
                                  project_to=correction_low_C, level=1.618)
        # syarat tp valid: price breaks_out(bullish_div_hit_tp.tp_price, min_extension=1.2)
        return {"entry": entry, "sl": sl, "tp": tp}

# ============ METODE 3: HIDDEN BULLISH DIVERGENCE (ABCDE) ============
def hidden_bullish_divergence(price, indicator):
    pattern_found = detect_consolidation_pattern(price)  # triangle/flag/pennant, min. 5 legs A-B-C-D-E
    if not pattern_found:
        return None
    price_higher = price.trend_up_in_pattern()
    indicator_lower = any(ind.trend_down_in_pattern() for ind in [RSI, MACD, AO])
    is_hidden = price_higher and indicator_lower
    zone_E = fibonacci_retracement(low=point_C, high=point_D, levels=[0.6, 0.7])
    if is_hidden and price.in_zone(zone_E) and confirm_candle:
        entry = confirm_candle.close
        sl = point_A_low  # SL selalu di low A, bukan C atau E
        tp = fibonacci_extension(low=point_A_low, high=point_A, levels=[1.0, 1.2])
        # syarat tp valid: price breaks_out(level_1_0)
        # jika breakdown dari low A sebelum breakout -> CUT LOSS, re-plot sebagai bullish divergence baru
        return {"entry": entry, "sl": sl, "tp": tp}

# ============ FILTER SCREENER ============
def screener_universe(stock):
    return (
        stock.currentPrice < 1000
        and stock.exchange in IDX_EXCHANGES
        and stock.regularMarketVolume * stock.currentPrice >= MIN_RUPIAH_LIQUIDITY  # proxy likuiditas
        and stock.quoteType == "EQUITY"
    )
```

---

## 8. Ringkasan Perbandingan 3 Metode

| Aspek | Metode 1: Bullish Divergence | Metode 2: Correction | Metode 3: Hidden Bullish Divergence |
|---|---|---|---|
| Konteks market | Downtrend / reversal | Setelah bullish div kena TP (pullback) | Uptrend / continuation |
| Struktur | 5 wave (1-2-3-4-5) | A-B-C | A-B-C-D-E (butuh pola konsolidasi dulu) |
| SL | Low candle konfirmasi | Low invalidation (lebih jauh) | Low A |
| TP | Fib 0.5–0.7 (retracement dari high wave-4 ke low wave-5) | Fib ext. 1.618 (syarat breakout) | Fib 1.0–1.2 (syarat breakout) |
| Risk & Reward | Sedang | **Terbesar** (SL & TP sama-sama terjauh) | Sedang, tapi entry lebih awal dari breakout |
| Cocok untuk | Trader suka beli di titik terbawah / reversal | Trader suka nyicil & hold jangka menengah | Trader suka ikut tren naik / bitover |

---


**Alur retrieval yang disarankan:** saat model reasoning (tahap 5, §0) diminta menjelaskan sebuah sinyal, sistem mengambil baris terkait dari `divergence_signal` + `price_snapshot` (beberapa candle terakhir) + rules dari dokumen ini (§3–§6), lalu menyisipkannya sebagai konteks di prompt. Model **tidak** menghitung ulang Fibonacci/SL/TP — angka-angka itu sudah final dari tahap kode (§0, tahap 3), model hanya menyusun kalimat penjelasan berdasarkan angka yang sudah benar. Ini mencegah LLM "mengarang" ulang angka yang seharusnya presisi.

**Cara mendapatkan angka akurasi yang JUJUR:** isi `backtest_result` dengan menjalankan logika §7 (pseudocode → kode nyata) terhadap data historis price_snapshot minimal 2–3 tahun ke belakang per metode per timeframe, lalu hitung `win_rate_pct` sungguhan. Jangan menulis angka target (95%, dst) di tabel sebelum ada hasil backtest — kolom itu diisi sesudah proses berjalan, bukan diasumsikan di depan.

---

## 8c. Backtest Engine — Spesifikasi Lengkap (agar hasil VALID, bukan agar hasil TINGGI)

> **Prinsip yang tidak bisa ditawar:** tugas backtest adalah **mengukur**, bukan **menghasilkan angka tertentu**. Sebuah backtest yang didesain supaya "pasti" keluar >95% hampir selalu mengandung salah satu dari cacat berikut — dan kalau kamu pakai data itu untuk trading uang asli, kamu akan rugi lebih parah karena mengira strategi ini jauh lebih aman dari kenyataannya:
>
> | Cacat Umum | Kenapa Bikin Angka Palsu Tinggi |
> |---|---|
> | **Lookahead bias** | Kode "mengintip" harga candle yang belum close saat itu (mis. pakai `high`/`low` candle hari ini untuk syarat entry yang seharusnya baru diketahui besok) |
> | **Survivorship bias** | Hanya backtest saham yang masih listing sekarang, padahal saham yang delisting/suspend (biasanya karena turun terus) tidak ikut dihitung → win rate jadi palsu tinggi |
> | **Overfitting parameter** | Level Fib "0.6/0.7" atau "1.618" di-utak-atik terus sampai pas dengan data historis yang SAMA dipakai untuk uji → begitu dipakai data baru, hancur |
> | **Cherry-picking periode** | Backtest cuma di periode bull market yang enak, skip periode sideways/bear | 
> | **Slippage & fee diabaikan** | Entry price di backtest = harga ideal candle, padahal eksekusi order riil beda (spread bid-ask, antrian) |
>
> Desain di bawah ini secara eksplisit mencegah kelima hal itu.

### 8c.1 Kebutuhan Data

```
- Data OHLCV per timeframe (1D, 4H, 1H, 45m, 30m) minimal 3-5 tahun ke belakang
- WAJIB termasuk saham yang sudah delisting/suspend dalam rentang waktu tsb
  (survivorship-bias-free universe) — jangan hanya pakai daftar saham aktif hari ini
- Data corporate action (stock split, reverse split) sudah di-adjust,
  supaya level Fibonacci/support-resistance historis tidak "patah" gara-gara split
```

### 8c.2 Aturan Anti-Lookahead (paling kritis)

```python
# SALAH (lookahead bias):
if candle[t].low == min(candle[t-5:t+1].low):  # pakai info masa depan (t+1 belum kejadian saat t)
    entry_signal = True

# BENAR — sinyal HANYA boleh pakai data sampai candle[t] yang SUDAH CLOSE:
def is_confirm_candle_valid(candle_t, timeframe, current_sim_time):
    candle_close_time = get_close_time(candle_t.ts, timeframe)  # sesuai tabel §6
    assert candle_close_time <= current_sim_time, "Lookahead violation: candle belum close"
    return (
        candle_t.close > candle_t.open           # hijau
        and has_real_body(candle_t)                # bukan doji, §3.3 poin 1
        and body_ratio(candle_t) >= MIN_BODY_RATIO  # threshold badan minimal, mis. body >= 30% dari range
    )

# Entry price simulasi = OPEN candle BERIKUTNYA setelah candle konfirmasi close
# (bukan close candle konfirmasi itu sendiri) — supaya realistis:
# di dunia nyata, begitu candle jam 10:00 close, order baru bisa dieksekusi mulai jam 10:00/10:01
entry_price_sim = next_candle.open
```

### 8c.3 Implementasi Rule per Metode (mengikuti §3–§5 persis)

```python
def backtest_bullish_divergence(price_series, indicator_series, timeframe):
    trades = []
    for t in range(WAVE_LOOKBACK, len(price_series)):
        # 1. Deteksi 5-wave turun s.d. candle t (hanya pakai data <= t)
        waves = detect_5_wave_decline(price_series[:t+1])
        if not waves.is_wave5_complete():
            continue

        # 2. Cek divergence pada wave 5 (harga lower-low, indikator higher-low)
        if not (price_series[t].low < waves.wave3_low
                and indicator_makes_higher_low(indicator_series[:t+1], waves)):
            continue

        # 3. Candle konfirmasi HARUS candle setelah wave-5 terbentuk & sudah close
        confirm = price_series[t]
        if not is_confirm_candle_valid(confirm, timeframe, current_sim_time=confirm.close_time):
            continue  # kalau doji -> skip, tunggu candle berikutnya (LOOP LANJUT, bukan entry)

        # 4. Entry, SL, TP sesuai §3.3-§3.5 — SEMUA dihitung dari data s.d. candle t saja
        entry = price_series[t+1].open if t+1 < len(price_series) else None
        if entry is None:
            continue
        sl = confirm.low
        fib_zone = fibonacci_retracement(low=waves.wave5_low, high=waves.wave4_high, levels=[0.5,0.6,0.7])
        tp_min = fib_zone[0.6]

        # 5. Simulasikan forward bar-by-bar (TIDAK boleh intip candle setelah entry saat menghitung SL/TP)
        outcome = simulate_forward(price_series, start_idx=t+1, entry=entry, sl=sl, tp=tp_min,
                                    max_hold_bars=MAX_HOLD)  # exit di SL/TP/timeout, mana duluan
        trades.append({
            "symbol": ..., "timeframe": timeframe, "entry_ts": price_series[t+1].ts,
            "entry": entry, "sl": sl, "tp": tp_min, "outcome": outcome.result,  # 'TP'|'SL'|'TIMEOUT'
            "rr": outcome.realized_rr, "bars_held": outcome.bars_held
        })
    return trades

# Fungsi sejenis dibuat utk: backtest_double_bullish_divergence (§3.6),
# backtest_correction (§4), backtest_hidden_bullish_divergence (§5) —
# masing-masing copy rule invalidasi & TP-nya PERSIS dari bagian §3-§5,
# termasuk syarat breakout untuk TP jauh, dan aturan "max Double, no Triple/Quadruple".

def simulate_forward(price_series, start_idx, entry, sl, tp, max_hold_bars):
    for i in range(start_idx, min(start_idx + max_hold_bars, len(price_series))):
        bar = price_series[i]
        # Asumsi konservatif kalau SL & TP sama-sama kena di 1 bar yang sama: SL menang dulu
        # (worst-case assumption, supaya backtest tidak over-optimis)
        if bar.low <= sl:
            return Outcome(result="SL", realized_rr=-1, bars_held=i-start_idx)
        if bar.high >= tp:
            return Outcome(result="TP", realized_rr=(tp-entry)/(entry-sl), bars_held=i-start_idx)
    return Outcome(result="TIMEOUT", realized_rr=(price_series[i].close-entry)/(entry-sl), bars_held=max_hold_bars)
```

### 8c.4 Biaya Transaksi (wajib dimasukkan, jangan diabaikan)

```
entry_price_realistic = entry_price_sim * (1 + slippage_pct)   -- slippage estimasi 0.1-0.3% saham likuiditas sedang
exit_price_realistic  = exit_price_sim  * (1 - slippage_pct)
fee_beli  = entry_price_realistic * lot * broker_fee_buy_pct    -- umumnya ~0.15-0.19% di broker IDX
fee_jual  = exit_price_realistic  * lot * broker_fee_sell_pct   -- umumnya ~0.25-0.29% (termasuk PPh final 0.1%)
net_pnl = (exit_price_realistic - entry_price_realistic) * lot - fee_beli - fee_jual
```
Tanpa langkah ini, win rate & RR yang keluar akan **selalu lebih bagus dari kenyataan** — karena biaya transaksi saham second-liner harga rendah bisa signifikan relatif terhadap size gerakan harganya.

### 8c.5 Validasi Anti-Overfitting: Walk-Forward, bukan Single-Pass

```
Jangan: tuning level Fib (0.6 vs 0.7, dst) dan test-nya di dataset yang SAMA.
Wajib:  Walk-forward split —
  Periode 1 (in-sample, mis. 2019-2022): tuning/observasi rule sesuai §3-§5 (level Fib TETAP sesuai
           yang diajarkan di transkrip — TIDAK boleh diubah-ubah cuma supaya cocok data)
  Periode 2 (out-of-sample, mis. 2023-2024): jalankan rule yang SAMA tanpa modifikasi apapun,
           catat hasilnya sebagai metrik yang dipercaya
  Periode 3 (holdout final, mis. 2025-sekarang): sentuh HANYA SEKALI di akhir, jadi "ujian akhir"
Kalau performa out-of-sample jauh lebih jelek dari in-sample -> tanda overfitting, JANGAN dipakai live.
```

### 8c.6 Metrik yang Wajib Dilaporkan (isi ke tabel `backtest_result`, §8b)

```
- win_rate_pct           = win_count / total_signals * 100
- avg_rr                 = rata-rata realized_rr semua trade (termasuk yang loss, RR = -1)
- expectancy             = (win_rate * avg_win_rr) - (loss_rate * avg_loss_rr)   -- HARUS positif
- max_drawdown_pct        = penurunan ekuitas terbesar berturut-turut
- sample_size             = total_signals   -- kalau < 30 per metode/timeframe, hasil TIDAK signifikan
                             secara statistik, jangan buru-buru percaya angkanya
- profit_factor           = total_profit / total_loss
- per metode (§3/§3.6/§4/§5) DAN per timeframe (§6) DIPISAH — jangan digabung rata,
  karena karakteristik risk/reward tiap kombinasi beda (lihat §8, tabel perbandingan)
```

### 8c.7 Interpretasi Angka — Kalibrasi Ekspektasi

```
- Win rate 45-55% dengan average RR > 1.5-2 dan expectancy positif = strategi SEHAT dan layak
  dipertimbangkan, meskipun jauh dari 95%.
- Win rate di atas 80-90% pada strategi price-action/Fibonacci diskresioner seperti ini adalah
  TANDA BAHAYA (kemungkinan besar ada bias di §8c.2-8c.5 yang belum ketutup), bukan tanda bagus —
  cek ulang seluruh pipeline sebelum percaya angkanya.
- Fokus optimasi yang benar: bukan menaikkan win_rate ke angka tertentu, tapi menaikkan EXPECTANCY
  dan menjaga max_drawdown tetap terkendali sesuai toleransi risiko kamu.
```

---

## 9. Catatan Penutup / Batasan Metodologi

- Strategi ini **tidak memakai** analisis fundamental, bandarmologi, atau volume sebagai basis sinyal — murni price action (candle) + 1 dari 3 indikator momentum (RSI/MACD/AO) + Fibonacci.
- Elliott Wave hanya dipakai sebagai *penamaan/plotting* posisi (1-2-3-4-5 / A-B-C / A-B-C-D-E), **bukan** basis keputusan entry — basis keputusan entry tetap selalu kembali ke divergence + candle konfirmasi + level Fibonacci.
- Tidak ada jaminan win-rate/akurasi tertentu; pengajar sendiri menyatakan sejauh sesi berjalan (~30+ emiten contoh) belum ada yang kena stop loss di kelas tsb — namun ini adalah klaim anekdotal dari sample kecil dan periode waktu terbatas, bukan hasil backtest formal berstatistik. Selalu lakukan validasi/backtest independen sebelum menerapkan modal riil, dan gunakan position sizing/money management yang disiplin (lihat §3.7) karena tidak ada strategi yang bebas risiko kerugian.
- **Memilih model LLM tertentu untuk membaca/menjelaskan strategi ini TIDAK mengubah akurasinya.** Akurasi hanya bisa didapat dari backtest nyata (tabel `backtest_result` di §8b, metodologi §8c) dan disiplin eksekusi (SL/TP/position sizing). Perlakukan tabel §0 sebagai *pembagian tugas engineering* (mana yang butuh kode, mana yang butuh bahasa), bukan sebagai jaminan hasil trading.
- **Tidak ada desain backtest yang bisa dipesan untuk keluar angka >95%.** Backtest yang jujur bisa keluar angka berapa saja — tugasnya mengukur, bukan mengonfirmasi harapan. Kalau hasil backtest §8c keluar jauh di bawah 95% (paling wajar: win rate 40-60% dengan RR sehat), itu **bukan berarti backtest-nya salah** — itu justru gambaran realistis trading diskresioner. Curigai justru kalau hasilnya konsisten di atas 90%: cek ulang §8c.2 (lookahead), §8c.4 (biaya transaksi), dan §8c.5 (overfitting) sebelum dipakai modal riil.