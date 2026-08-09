# Data Sources

## 1. Provider MVP: yfinance

Dipilih karena mudah dipakai dengan Python dan cocok untuk historical
OHLCV. **Konfirmasi kebutuhan:** timeframe yang dipakai adalah **15m ke
atas** (15m, 30m, 1H, 4H, Daily, Weekly, Monthly) — tidak ada kebutuhan
1m/tick real-time, jadi keterbatasan yfinance di data intraday super
granular **bukan masalah** untuk proyek ini.

### Format ticker

```
IDX : BBCA.JK, BBRI.JK, BMRI.JK, TLKM.JK, ...  (suffix .JK wajib)
US  : AAPL, NVDA, TSLA, MSFT, ...              (tanpa suffix)
```

### Batasan yfinance yang tetap perlu diperhatikan

- Interval intraday (15m/30m/1H) di yfinance biasanya dibatasi rentang
  historis (umumnya beberapa minggu-bulan ke belakang tergantung
  interval) — cek ulang batas ini saat implementasi, jangan asumsikan
  bisa tarik intraday bertahun-tahun ke belakang.
- Bisa terjadi rate limiting kalau fetch terlalu banyak ticker sekaligus
  dalam waktu singkat — gunakan batching + delay, dan **wajib** pakai
  cache layer (§3) supaya tidak fetch ulang data yang sama di hari yang
  sama.
- Data historis kadang direvisi (adjusted close berubah) — untuk
  backtesting, ambil snapshot yang konsisten, jangan re-fetch tiap kali
  run backtest yang sama.

## 2. Provider Abstraction

```python
# providers/base.py
class DataProvider(ABC):
    @abstractmethod
    def get_ohlcv(
        self, symbol: str, timeframe: str,
        start: datetime, end: datetime
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def get_last_price(self, symbol: str) -> float:
        ...
```

`strategies/`, `market_structure/`, dan modul lain **hanya boleh**
bergantung pada interface ini, tidak pernah import `yfinance` langsung.
Ini memastikan kalau nanti perlu ganti/tambah provider (misal butuh data
lebih real-time untuk fitur baru), tidak ada perubahan di strategy
engine.

```
DataProvider (interface)
    │
    └── YFinanceProvider (implementasi MVP)
```

## 3. Caching Layer

Karena universe bisa ribuan ticker (IDX + US), cache wajib ada dari awal
supaya Morning Scanner tidak fetch ulang semua data tiap kali dijalankan.

```
CacheProvider(DataProvider) wraps YFinanceProvider
    ↓
get_ohlcv(symbol, tf, start, end):
    1. Cek data/cache/{symbol}_{tf}.parquet
    2. Kalau ada & sudah termasuk range yang diminta → return dari cache
    3. Kalau belum → fetch bagian yang kurang saja dari provider,
       merge, simpan ulang ke cache
```

Simpan cache per simbol+timeframe dalam format parquet (bukan CSV) untuk
efisiensi baca/tulis. Invalidasi cache otomatis untuk candle hari
berjalan (belum closed), tapi candle yang sudah closed boleh disimpan
permanen.

## 4. Stock Universe

Universe **tidak boleh** hardcode hanya beberapa ticker di kode. Simpan
di `config/universe.yaml`:

```yaml
idx:
  source: "list"            # atau "index_constituents" (mis. IDX30, LQ45)
  tickers:
    - BBCA.JK
    - BBRI.JK
    - BMRI.JK
    - TLKM.JK
    # ...

us:
  source: "list"            # atau "sp500", "nasdaq100"
  tickers:
    - AAPL
    - NVDA
    - TSLA
    - MSFT
    # ...
```

Untuk versi lanjutan, `source: "index_constituents"` bisa dipakai untuk
otomatis narik daftar konstituen index (misal LQ45, S&P 500) daripada
maintain list manual — tapi ini bukan prioritas MVP.

## 5. Liquidity Pre-filter

Sebelum data OHLCV lengkap diambil untuk full pipeline analisis, filter
dulu berdasarkan:

```yaml
liquidity_filter:
  min_avg_volume_20d: 1000000     # sesuaikan per market (IDX vs US beda skala)
  min_price: 50                    # hindari saham gocap/penny stock kalau tidak diinginkan
```

Ini mengurangi jumlah ticker yang harus melalui pipeline mahal
(market_structure + strategy engine) tiap pagi.

## 6. Update Schedule

```
Morning Scanner   : dijalankan 1x sebelum market open (misal jam 08:00 WIB untuk IDX)
Live Scanner      : polling tiap candle close dari timeframe terkecil yang dipantau
                     (default 15m → polling tiap 15 menit selama market jam)
EOD refresh       : setelah market close, tarik candle Daily final + update cache
```

Jadwal ini diatur lewat `scanner/scheduler.py`, dikonfigurasi via
environment variable / config, bukan hardcoded jam di kode.