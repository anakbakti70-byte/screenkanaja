"""
==============================================================================
TECHNICAL_LOGIC.PY — SOURCE OF TRUTH / OTAK INTI (SINGLE SOURCE OF TRUTH)
==============================================================================
Semua formula, deteksi pattern, rules entry/SL/TP, dan freshness engine untuk
seluruh metode CTG (Bullish Divergence, Double Bullish Divergence,
Correction/ABC, Hidden Bullish Divergence/ABCDE) ADA DI SINI.

scanner_core.py TIDAK BOLEH punya rumus duplikat — ia hanya orchestrator yang
memanggil fungsi-fungsi di file ini.

Perbaikan utama dibanding versi lama:
1. Pattern detection dan entry decision DIPISAH secara eksplisit lewat
   SignalStatus.WAITING_CONFIRMATION — pattern yang belum keluar candle
   konfirmasi TIDAK dibuang (None), tapi disimpan sebagai kandidat historis,
   sesuai prinsip "historical_detection != actionable_entry".
2. Ada METHOD_CONFIG terpusat: setiap metode (Bullish, Double Bullish,
   Correction, Hidden) punya karakteristik freshness/price-distance sendiri,
   bukan angka pukul rata.
3. Ada validate_signal_freshness() sebagai SATU-SATUNYA validator status
   sinyal (DETECTED/WAITING_CONFIRMATION/READY/VALID/STALE/INVALID) dipakai
   oleh seluruh strategy & scanner_core — tidak ada logika status ganda.
4. Confirmation candle window dibatasi (confirmation_window) — sesuai materi
   Day 1/Day 2: "confirmation yang sudah lama juga harus mempunyai freshness".
   Kalau pattern sudah terdeteksi tapi tidak pernah keluar cendol dalam
   window tsb, sinyal dianggap EXPIRED/INVALID, bukan menunggu selamanya.
5. Indicator confirmation memakai fallback AO -> RSI -> MACD (cukup SATU
   indikator yang confirm — sesuai materi: "one aja, cukup satu saja").
6. Double Bullish Divergence dan Hidden Bullish Divergence sekarang punya
   implementasi ASLI masing-masing (sebelumnya cuma inherit tanpa logika
   tambahan apa pun — bug konseptual yang membuat kedua metode itu
   sebenarnya tidak pernah benar-benar dievaluasi sesuai teorinya).
7. Tidak ada look-ahead: seluruh pencarian confirmation candle & swing point
   hanya menggunakan indeks candle yang SUDAH terjadi (<= latest candle yang
   dikirim scanner), tidak pernah menembak balik ke masa lalu memakai data
   yang belum ada saat itu.

CATATAN PENTING (harus dibaca sebelum mengubah parameter):
Nilai-nilai di METHOD_CONFIG (max_signal_age, confirmation_window,
price_distance_max_pct, price_distance_atr_mult) adalah hasil interpretasi
saya terhadap penjelasan kualitatif di kelas CTG (mis. "correction punya SL
paling jauh tapi target paling jauh juga", "double bullish butuh gerakan
lebih cepat karena sudah gagal sekali"). Kelas TIDAK memberi angka pasti
untuk parameter-parameter freshness ini (memang secara historis engine lama
tidak punya freshness engine sama sekali). Jadi anggap angka-angka ini
sebagai default yang masuk akal dan MUDAH DI-TUNING, bukan aturan baku CTG.
==============================================================================
"""

import math
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from app.strategies.base import BaseStrategy, SetupResult


# ==============================================================================
# STATUS SINYAL (SINGLE SOURCE OF TRUTH UNTUK SELURUH STATUS)
# ==============================================================================

class SignalStatus:
    """Status lifecycle sinyal. Dipakai oleh SEMUA strategy dan scanner_core."""
    DETECTED = "DETECTED"                    # pola historis terdeteksi, belum tentu actionable
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"  # pola valid, menunggu candle konfirmasi (cendol)
    READY = "READY"                           # entry baru terbentuk PERSIS di candle terbaru (age = 0)
    VALID = "VALID"                           # entry masih fresh & actionable (age > 0 tapi < max_age)
    STALE = "STALE"                           # entry sudah terlalu tua / harga sudah lari terlalu jauh
    INVALID = "INVALID"                       # struktur pattern sudah rusak (SL tembus / pattern gagal)


# ==============================================================================
# METHOD CONFIG — KARAKTERISTIK FRESHNESS PER METODE (BUKAN ANGKA PUKUL RATA)
# ==============================================================================
# Struktur: setiap parameter freshness bisa berupa dict {timeframe: nilai, "default": nilai}
# atau angka tunggal. Resolusinya lewat _resolve_timeframe_param().

METHOD_CONFIG: Dict[str, Dict[str, Any]] = {
    "Bullish Divergence": {
        # Semakin besar timeframe, semakin "berat" per candle-nya -> umur maksimal boleh
        # lebih pendek dalam hitungan CANDLE (bukan waktu), karena 1 candle daily itu berat.
        "max_signal_age": {"default": 5, "1d": 3, "4h": 4, "1h": 6, "30m": 8, "15m": 8},
        "confirmation_window": {"default": 5, "1d": 3, "4h": 5, "1h": 8, "30m": 10, "15m": 10},
        "price_distance_max_pct": 0.03,   # sesuai SOP lama: "max 3% chase limit"
        "price_distance_atr_mult": 1.5,
        "min_confirmation_body_ratio": 0.3,   # candle hijau wajib berbadan, doji ditolak
        "min_risk_reward": 1.0,               # kelas menekankan idealnya >= 1:3, tapi hard floor 1:1
    },
    "Double Bullish Divergence": {
        # Double bullish = sinyal susulan setelah gagal capai target 0.5 -> harus lebih gesit,
        # karena semakin lama gagal ditindaklanjuti, makin besar risiko jadi 3=5 (double top palsu).
        "max_signal_age": {"default": 4, "1d": 2, "4h": 3, "1h": 5, "30m": 6, "15m": 6},
        "confirmation_window": {"default": 4, "1d": 2, "4h": 4, "1h": 6, "30m": 8, "15m": 8},
        "price_distance_max_pct": 0.025,
        "price_distance_atr_mult": 1.25,
        "min_confirmation_body_ratio": 0.3,
        "min_risk_reward": 1.0,
    },
    "Correction (ABC)": {
        # Correction: SL paling jauh dari semua metode (materi Day 2), makanya sabar lebih lama
        # juga diberi toleransi umur & jarak harga paling longgar dari semua metode.
        "max_signal_age": {"default": 8, "1d": 5, "4h": 6, "1h": 10, "30m": 12, "15m": 12},
        "confirmation_window": {"default": 8, "1d": 5, "4h": 8, "1h": 12, "30m": 14, "15m": 14},
        "price_distance_max_pct": 0.04,
        "price_distance_atr_mult": 1.75,
        "min_confirmation_body_ratio": 0.3,
        "min_risk_reward": 1.0,
    },
    "Hidden Bullish Divergence (ABCDE)": {
        # Hidden butuh pattern continuation (segitiga) dulu -> umur menengah antara
        # bullish reguler dan correction.
        "max_signal_age": {"default": 6, "1d": 4, "4h": 5, "1h": 8, "30m": 10, "15m": 10},
        "confirmation_window": {"default": 6, "1d": 4, "4h": 6, "1h": 10, "30m": 12, "15m": 12},
        "price_distance_max_pct": 0.03,
        "price_distance_atr_mult": 1.5,
        "min_confirmation_body_ratio": 0.3,
        "min_risk_reward": 1.0,
    },
}


def _resolve_timeframe_param(config: Dict[str, Any], key: str, timeframe: str, fallback: float = 5) -> float:
    """Ambil parameter yang bisa berbentuk dict-per-timeframe ATAU angka tunggal."""
    val = config.get(key, fallback)
    if isinstance(val, dict):
        return val.get(timeframe, val.get("default", fallback))
    return val


# ==============================================================================
# LOGIKA TEKNIKAL DASAR - SOURCE OF TRUTH (Brain)
# ==============================================================================

def calculate_fib_levels(start: float, end: float, levels: List[float]) -> Dict[float, float]:
    """Fibonacci retracement/proyeksi: level 0 = start, level 1 = end.
    Level > 1 dipakai untuk proyeksi/ancer-ancer di luar range start-end
    (contoh: level 1.2/1.4/1.6/2.0 pada materi Day 1 untuk mencari
    ancer-ancer penurunan lanjutan / titik invalidasi double bullish)."""
    diff = end - start
    return {level: start + (diff * level) for level in levels}


def calculate_fib_extension(point_a: float, point_b: float, point_c: float, levels: Optional[List[float]] = None) -> Dict[float, float]:
    """Proyeksi Fibonacci extension: mengukur leg A->B lalu memproyeksikannya
    dari titik C (dipakai untuk TP correction & TP jauh double bullish)."""
    if levels is None:
        levels = [0.618, 1.0, 1.618]
    diff = point_b - point_a
    return {level: point_c + (diff * level) for level in levels}


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — dipakai sebagai basis dinamis price-distance
    validation (poin 15 final prompt: jangan pakai angka tetap yang tidak
    sesuai karakteristik volatilitas saham saat ini)."""
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()


def get_swing_low_since(df: pd.DataFrame, after_idx: int, before_idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Cari swing low (harga terendah) setelah after_idx, opsional dibatasi
    sebelum before_idx (dipakai Double Bullish untuk membatasi pencarian L1
    hanya sampai sebelum siklus berikutnya mulai, supaya tidak look-ahead
    campur siklus)."""
    start = after_idx + 1
    end = before_idx if before_idx is not None else len(df)
    end = min(end, len(df))
    if start >= end:
        return None
    window = df["Low"].iloc[start:end]
    if window.empty:
        return None
    rel_pos = int(window.values.argmin())
    idx = start + rel_pos
    return {"idx": idx, "price": float(window.iloc[rel_pos])}


def get_swing_high_since(df: pd.DataFrame, after_idx: int, before_idx: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Sama seperti get_swing_low_since tapi untuk swing high (dipakai Hidden
    Bullish Divergence & pencarian rally-high pada Double Bullish)."""
    start = after_idx + 1
    end = before_idx if before_idx is not None else len(df)
    end = min(end, len(df))
    if start >= end:
        return None
    window = df["High"].iloc[start:end]
    if window.empty:
        return None
    rel_pos = int(window.values.argmax())
    idx = start + rel_pos
    return {"idx": idx, "price": float(window.iloc[rel_pos])}


def is_confirmation_candle(df: pd.DataFrame, idx: int, min_body_ratio: float = 0.3) -> bool:
    """Candle konfirmasi ("cendol") sesuai materi Day 1:
    - WAJIB candle hijau (Close > Open)
    - WAJIB berbadan minimal min_body_ratio dari range total (default 30%)
    - Doji (body sangat kecil) WAJIB ditolak — "doji itu enggak boleh karena
      doji artinya masih bingung"."""
    if idx < 0 or idx >= len(df):
        return False
    row = df.iloc[idx]
    if row["Close"] <= row["Open"]:
        return False
    body = row["Close"] - row["Open"]
    range_ = row["High"] - row["Low"]
    if range_ <= 0:
        return False
    body_ratio = body / range_
    # Doji eksplisit: body_ratio sangat kecil (< 5% dari range) selalu ditolak,
    # apapun nilai min_body_ratio yang dipakai caller.
    if body_ratio < 0.05:
        return False
    return body_ratio >= min_body_ratio


def find_confirmation_candle(df: pd.DataFrame, start_idx: int, search_window: int) -> Optional[int]:
    """Cari candle konfirmasi PERTAMA setelah start_idx, dibatasi search_window
    candle ke depan (bukan unbounded search sampai akhir df). Ini mencegah
    scanner tiba-tiba "menemukan" konfirmasi dari pattern yang sudah sangat
    tua lalu memperlakukannya sebagai entry baru (anti-stale-signal, poin 16
    final prompt)."""
    end = min(start_idx + 1 + search_window, len(df))
    for i in range(start_idx + 1, end):
        if is_confirmation_candle(df, i):
            return i
    return None


def _first_confirming_indicator(
    indicators: Dict[str, pd.Series],
    idx_early: int,
    idx_late: int,
    expect_higher_at_late: bool,
) -> Optional[str]:
    """Helper tunggal untuk cek divergence indikator, dipakai oleh SEMUA
    strategy (tidak ada rumus divergence duplikat di file lain).
    Prioritas: AO -> RSI -> MACD, cukup SATU yang confirm (sesuai materi:
    "Apakah harus tiga-tiganya terfirm? Tidak, cukup satu saja").

    expect_higher_at_late=True  -> dipakai untuk regular/double bullish divergence
                                    (harga lower-low, indikator higher-low)
    expect_higher_at_late=False -> dipakai untuk hidden bullish divergence
                                    (harga higher-high, indikator lower-high)
    """
    for name in ("AO", "RSI", "MACD"):
        series = indicators.get(name)
        if series is None:
            continue
        if idx_early < 0 or idx_late < 0 or idx_early >= len(series) or idx_late >= len(series):
            continue
        v_early = series.iloc[idx_early]
        v_late = series.iloc[idx_late]
        if pd.isna(v_early) or pd.isna(v_late):
            continue
        if expect_higher_at_late and v_late > v_early:
            return name
        if not expect_higher_at_late and v_late < v_early:
            return name
    return None


# ==============================================================================
# VALIDATOR TERPUSAT — SATU-SATUNYA TEMPAT MENENTUKAN STATUS AKHIR SINYAL
# ==============================================================================

def validate_signal_freshness(
    setup: "SetupResult",
    latest_idx: int,
    current_price: float,
    atr_value: Optional[float],
    method_config: Dict[str, Any],
) -> Tuple[str, str]:
    """SATU-SATUNYA fungsi yang menentukan status akhir sebuah sinyal.
    scanner_core.py HANYA memanggil fungsi ini, tidak boleh punya logika
    status sendiri (poin 18/19/20 final prompt: scanner_core = orchestrator,
    technical_logic = single source of truth untuk validasi).

    Return: (status: str, reason: str)
    """

    # --- Kasus 1: pattern terdeteksi tapi belum ada candle konfirmasi ---
    if setup.status == SignalStatus.WAITING_CONFIRMATION:
        bars_since_pattern = latest_idx - setup.pattern_candle_index
        window = _resolve_timeframe_param(method_config, "confirmation_window", setup.timeframe)
        if bars_since_pattern > window:
            return (
                SignalStatus.INVALID,
                f"Pattern terdeteksi di candle {setup.pattern_candle_index} namun tidak ada "
                f"candle konfirmasi (cendol berbadan) dalam {window} candle. "
                f"Sinyal kedaluwarsa sebelum sempat actionable (bukan look-ahead, murni basi)."
            )
        return (
            SignalStatus.WAITING_CONFIRMATION,
            "Pattern valid secara struktur & indikator, menunggu candle konfirmasi "
            "(candle hijau berbadan, bukan doji) sebelum bisa dianggap entry."
        )

    # --- Kasus 2: sudah punya entry_price/stop_loss -> cek invalidation dulu ---
    if setup.stop_loss is not None and not (isinstance(setup.stop_loss, float) and math.isnan(setup.stop_loss)):
        if current_price < setup.stop_loss:
            return SignalStatus.INVALID, "Harga menembus Stop Loss / titik invalidasi struktur (pattern broken)."

    # --- Kasus 3: freshness umur sinyal ---
    signal_age = latest_idx - setup.entry_candle_index
    max_age = _resolve_timeframe_param(method_config, "max_signal_age", setup.timeframe)

    # --- Kasus 4: price distance dinamis (ATR jika tersedia, fallback persentase tetap) ---
    price_dist_pct = 0.0
    if setup.entry_price and setup.entry_price > 0:
        price_dist_pct = (current_price - setup.entry_price) / setup.entry_price

    max_dist_pct = method_config.get("price_distance_max_pct", 0.03)
    if atr_value and setup.entry_price and setup.entry_price > 0:
        atr_mult = method_config.get("price_distance_atr_mult", 1.5)
        atr_dist_pct = (atr_value * atr_mult) / setup.entry_price
        if atr_dist_pct > 0:
            # Pakai ambang yang LEBIH KETAT antara persentase tetap dan ATR-based,
            # supaya saat volatilitas rendah kita tidak terlalu longgar "menoleransi kejar harga".
            max_dist_pct = min(max_dist_pct, atr_dist_pct)

    if price_dist_pct > max_dist_pct:
        return (
            SignalStatus.STALE,
            f"Harga sudah lari +{price_dist_pct:.2%} dari entry point "
            f"(ambang dinamis {max_dist_pct:.2%}). Entry sudah terlewat, jangan dikejar."
        )

    if signal_age > max_age:
        return (
            SignalStatus.STALE,
            f"Signal basi ({signal_age} candle sejak entry candle, ambang {max_age} candle "
            f"untuk metode & timeframe ini)."
        )

    if signal_age == 0:
        return SignalStatus.READY, "Setup baru terbentuk PERSIS di candle terbaru. Entry fresh & actionable."

    return SignalStatus.VALID, "Entry masih fresh & actionable (dalam ambang freshness dan price-distance)."


def _waiting_result(
    strategy_name: str,
    symbol: str,
    timeframe: str,
    pattern_candle_index: int,
    metadata: Dict[str, Any],
) -> "SetupResult":
    """Bangun SetupResult untuk pattern yang valid secara struktur/indikator
    TAPI belum ada candle konfirmasi. entry_price/stop_loss/take_profit diisi
    NaN secara eksplisit (bukan angka dummy yang menyesatkan) supaya jelas
    field ini belum berlaku sampai konfirmasi muncul."""
    return SetupResult(
        status=SignalStatus.WAITING_CONFIRMATION,
        strategy_name=strategy_name,
        symbol=symbol,
        timeframe=timeframe,
        entry_price=float("nan"),
        stop_loss=float("nan"),
        take_profit=float("nan"),
        risk_reward=0.0,
        pattern_candle_index=pattern_candle_index,
        entry_candle_index=pattern_candle_index,  # placeholder: dipakai utk hitung "umur menunggu konfirmasi"
        metadata=metadata,
    )


# ==============================================================================
# STRATEGY: BULLISH DIVERGENCE (W1-W5)
# ==============================================================================

class BullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Bullish Divergence", config)

    def get_max_age(self, timeframe: str) -> int:
        # Dipertahankan untuk kompatibilitas pemanggil lama, tapi sekarang
        # HANYA delegasi ke METHOD_CONFIG (single source of truth), tidak ada
        # angka duplikat di sini.
        return int(_resolve_timeframe_param(METHOD_CONFIG[self.name], "max_signal_age", timeframe))

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        cfg = METHOD_CONFIG[self.name]
        if pivots.empty or len(df) < 20:
            return None

        symbol = df.attrs.get("symbol", "UNKNOWN")
        timeframe = df.attrs.get("timeframe", "UNKNOWN")

        # 1. DETEKSI STRUKTUR (W1-W4)
        try:
            w1 = pivots[pivots["movement_label"] == "W1"].iloc[-1]
            w2 = pivots[pivots["movement_label"] == "W2"].iloc[-1]
            w3 = pivots[pivots["movement_label"] == "W3"].iloc[-1]
            w4 = pivots[pivots["movement_label"] == "W4"].iloc[-1]
        except (IndexError, KeyError):
            return None

        # 2. DETEKSI W5 (Lowest Low setelah W4)
        # Penting: W5 harus lebih rendah dari W3 (Price Divergence secara struktur)
        w5_data = get_swing_low_since(df, int(w4["index"]))
        if w5_data is None or not (w5_data["price"] < w3["price"]):
            return None

        pattern_candle_index = int(w5_data["idx"])

        # 3. VERIFIKASI DIVERGENSI INDIKATOR (AO -> RSI -> MACD, cukup satu)
        confirming_indicator = _first_confirming_indicator(
            indicators, int(w3["index"]), pattern_candle_index, expect_higher_at_late=True
        )
        if confirming_indicator is None:
            return None

        base_metadata = {
            "pivots": {
                "W1": {"idx": int(w1["index"]), "price": float(w1["price"])},
                "W2": {"idx": int(w2["index"]), "price": float(w2["price"])},
                "W3": {"idx": int(w3["index"]), "price": float(w3["price"])},
                "W4": {"idx": int(w4["index"]), "price": float(w4["price"])},
                "W5": w5_data,
            },
            "indicator": confirming_indicator,
            "historical_bars_used": len(df),
        }

        # 4. CARI KONFIRMASI PERTAMA (First Actionable Entry), dibatasi confirmation_window
        window = int(_resolve_timeframe_param(cfg, "confirmation_window", timeframe))
        entry_idx = find_confirmation_candle(df, pattern_candle_index, window)

        if entry_idx is None:
            # Pattern & divergence valid, tapi belum ada cendol -> JANGAN dibuang.
            # Simpan sebagai kandidat historis yang masih menunggu konfirmasi.
            return _waiting_result(self.name, symbol, timeframe, pattern_candle_index, base_metadata)

        # 5. KALKULASI LEVEL ENTRY & TARGET
        entry_p = float(df["Close"].iloc[entry_idx])
        sl_p = float(df["Low"].iloc[entry_idx])  # SL = low candle konfirmasi (sesuai materi Day 1)
        tp_levels = calculate_fib_levels(w5_data["price"], w4["price"], [0.5, 0.6, 0.7])
        tp_p = tp_levels[0.6]  # target minimal 0.6 sesuai materi ("targetnya tuh di 0,6 teman-teman minimumnya")

        if not (sl_p < entry_p < tp_p):
            return None
        rr = (tp_p - entry_p) / (entry_p - sl_p) if (entry_p - sl_p) > 0 else 0.0
        if rr < cfg["min_risk_reward"]:
            return None

        base_metadata.update({
            "confirmation_candle": True,
            "tp_zone": tp_levels,
        })

        return SetupResult(
            status=SignalStatus.READY,  # status awal, akan divalidasi ulang oleh validate_signal_freshness()
            strategy_name=self.name,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=entry_p,
            stop_loss=sl_p,
            take_profit=tp_p,
            risk_reward=rr,
            pattern_candle_index=pattern_candle_index,
            entry_candle_index=entry_idx,
            metadata=base_metadata,
        )


# ==============================================================================
# STRATEGY: DOUBLE BULLISH DIVERGENCE
# ==============================================================================
# Definisi sesuai materi Day 1: Double Bullish Divergence terjadi ketika
# bullish divergence PERTAMA gagal mencapai target 0.5, lalu harga break
# down di bawah low candle konfirmasi pertama, membentuk low BARU yang
# kembali menunjukkan divergensi indikator dibanding low pertama.
# Invalidasi: Fibonacci level 2.0 dari leg (W4_prev -> L1).
# TP pendek: fib 0.5/0.6/0.7 dari leg (L2 -> rally high).
# TP jauh ("hutang"): proyeksi ulang leg asli (L1 -> W4_prev) dari L2, harus
# breakout di atas target 0.5 yang gagal dicapai sebelumnya.
# ==============================================================================

class DoubleBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Double Bullish Divergence", config)

    def get_max_age(self, timeframe: str) -> int:
        return int(_resolve_timeframe_param(METHOD_CONFIG[self.name], "max_signal_age", timeframe))

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        cfg = METHOD_CONFIG[self.name]
        if pivots.empty or len(df) < 30:
            return None

        symbol = df.attrs.get("symbol", "UNKNOWN")
        timeframe = df.attrs.get("timeframe", "UNKNOWN")

        try:
            w3_all = pivots[pivots["movement_label"] == "W3"]
            w4_all = pivots[pivots["movement_label"] == "W4"]
            if len(w3_all) < 2 or len(w4_all) < 2:
                # Butuh minimal DUA siklus W1-W4 untuk bisa membandingkan L1 vs L2
                return None
            w3_prev, w4_prev = w3_all.iloc[-2], w4_all.iloc[-2]
            w4_curr = w4_all.iloc[-1]
        except (IndexError, KeyError):
            return None

        # 1. Cari L1: swing low pertama setelah w4_prev, dibatasi sebelum siklus berikutnya mulai
        #    supaya tidak "look-ahead" mencampur dua siklus yang berbeda.
        l1_data = get_swing_low_since(df, int(w4_prev["index"]), before_idx=int(w4_curr["index"]))
        if l1_data is None or not (l1_data["price"] < w3_prev["price"]):
            return None

        # 2. Cari candle konfirmasi PERTAMA (bullish divergence pertama), dibatasi window metode Bullish
        bullish_window = int(_resolve_timeframe_param(METHOD_CONFIG["Bullish Divergence"], "confirmation_window", timeframe))
        l1_confirm_idx = find_confirmation_candle(df, int(l1_data["idx"]), bullish_window)
        if l1_confirm_idx is None or l1_confirm_idx >= int(w4_curr["index"]):
            return None
        l1_confirm_low = float(df["Low"].iloc[l1_confirm_idx])

        # 3. Target 0.5 dari leg w4_prev -> l1 (TP bullish divergence pertama)
        tp1_zone = calculate_fib_levels(l1_data["price"], w4_prev["price"], [0.5])
        tp1_target = tp1_zone[0.5]

        # 4. Rally high antara l1_confirm_idx dan sekarang (w4_curr index sbg batas atas cycle lama)
        search_end = max(int(w4_curr["index"]) + 1, l1_confirm_idx + 1)
        rally_high = float(df["High"].iloc[l1_confirm_idx:search_end].max())

        # SYARAT UTAMA DOUBLE BULLISH: rally GAGAL mencapai target 0.5.
        # Kalau target 0.5 sudah kena, ini BUKAN double bullish -- ini bullish
        # divergence reguler yang sudah "lunas" (sesuai istilah materi Day 1).
        if rally_high >= tp1_target:
            return None

        # 5. Harga harus break down di bawah low candle konfirmasi L1
        l2_data = get_swing_low_since(df, int(w4_curr["index"]))
        if l2_data is None or not (l2_data["price"] <= l1_confirm_low):
            return None

        pattern_candle_index = int(l2_data["idx"])

        # 6. Verifikasi indikator: L2 harus HIGHER LOW dibanding L1 (divergensi kedua)
        confirming_indicator = _first_confirming_indicator(
            indicators, int(l1_data["idx"]), pattern_candle_index, expect_higher_at_late=True
        )
        if confirming_indicator is None:
            return None

        base_metadata = {
            "l1": l1_data,
            "l1_confirm_index": l1_confirm_idx,
            "l1_confirm_low": l1_confirm_low,
            "rally_high": rally_high,
            "tp1_target_missed": tp1_target,
            "l2": l2_data,
            "indicator": confirming_indicator,
            "historical_bars_used": len(df),
        }

        # 7. Cari candle konfirmasi KEDUA (entry double bullish), dibatasi confirmation_window metode ini
        window = int(_resolve_timeframe_param(cfg, "confirmation_window", timeframe))
        entry_idx = find_confirmation_candle(df, pattern_candle_index, window)

        if entry_idx is None:
            return _waiting_result(self.name, symbol, timeframe, pattern_candle_index, base_metadata)

        entry_p = float(df["Close"].iloc[entry_idx])

        # 8. SL di Fibonacci level 2.0 dari leg (w4_prev -> l1) -- sesuai materi:
        #    "SL-nya di dua ... kalau dia melewati Fibo 2 ini juga biasa peneran lima kali lagi"
        sl_zone = calculate_fib_levels(w4_prev["price"], l1_data["price"], [2.0])
        sl_p = sl_zone[2.0]
        if not (sl_p < entry_p):
            return None

        # 9. TP pendek: fib 0.5/0.6/0.7 dari leg (l2 -> rally_high)
        tp_short_zone = calculate_fib_levels(l2_data["price"], rally_high, [0.5, 0.6, 0.7])
        tp_short = tp_short_zone[0.6]

        # 10. TP jauh ("hutang" dari bullish divergence pertama) -- proyeksi ulang leg asli
        #     (l1 -> w4_prev) dari l2, syarat breakout di atas tp1_target yang gagal dicapai.
        #     Interpretasi ini best-effort dari penjelasan kualitatif materi; dipakai HANYA
        #     sebagai info tambahan (bukan take_profit utama) karena rumus pasti tidak
        #     didiktekan angka eksaknya di kelas.
        tp_far_zone = calculate_fib_extension(l1_data["price"], w4_prev["price"], l2_data["price"], [1.0])
        tp_far = tp_far_zone[1.0]

        if not (sl_p < entry_p < tp_short):
            return None
        rr = (tp_short - entry_p) / (entry_p - sl_p) if (entry_p - sl_p) > 0 else 0.0
        if rr < cfg["min_risk_reward"]:
            return None

        base_metadata.update({
            "tp_short_zone": tp_short_zone,
            "tp_far_estimate": tp_far,
            "tp_far_breakout_level": tp1_target,
            "tp_far_note": (
                "TP jauh adalah estimasi 'hutang' dari bullish divergence pertama; "
                "baru berlaku sebagai target realistis jika harga breakout di atas "
                "tp_far_breakout_level (target 0.5 yang gagal dicapai sebelumnya)."
            ),
        })

        return SetupResult(
            status=SignalStatus.READY,
            strategy_name=self.name,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=entry_p,
            stop_loss=sl_p,
            take_profit=tp_short,
            risk_reward=rr,
            pattern_candle_index=pattern_candle_index,
            entry_candle_index=entry_idx,
            metadata=base_metadata,
        )


# ==============================================================================
# STRATEGY: CORRECTION ABC
# ==============================================================================

class CorrectionStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Correction (ABC)", config)

    def get_max_age(self, timeframe: str) -> int:
        return int(_resolve_timeframe_param(METHOD_CONFIG[self.name], "max_signal_age", timeframe))

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        cfg = METHOD_CONFIG[self.name]
        symbol = df.attrs.get("symbol", "UNKNOWN")
        timeframe = df.attrs.get("timeframe", "UNKNOWN")

        # Mencari struktur A-B (Impulse: A = low awal / low bullish sebelumnya, B = high / TP tercapai)
        lows = pivots[pivots["type"] == -1]
        highs = pivots[pivots["type"] == 1]
        if len(lows) < 1 or len(highs) < 1:
            return None

        A = lows.iloc[-1]
        B = highs.iloc[-1]
        if not (B["index"] > A["index"]):
            return None

        # Cari titik C (Retracement Zone 0.6 - 0.7 dari leg A->B)
        C_data = get_swing_low_since(df, int(B["index"]))
        if C_data is None:
            return None

        pattern_candle_index = int(C_data["idx"])
        fib = calculate_fib_levels(A["price"], B["price"], [0.6, 0.7])

        # Validasi Retracement Zone
        if not (fib[0.6] <= C_data["price"] <= fib[0.7] * 1.05):
            return None

        # Cek opsional: divergence indikator di titik C (bukan syarat wajib, tapi
        # "lebih bagus lagi jika ada bullish divergence" -- ditandai di metadata
        # sebagai penambah confidence, bukan penggagal setup jika tidak ada.
        confluence_indicator = _first_confirming_indicator(
            indicators, int(A["index"]), pattern_candle_index, expect_higher_at_late=True
        )

        base_metadata = {
            "pivots": {
                "A": {"idx": int(A["index"]), "price": float(A["price"])},
                "B": {"idx": int(B["index"]), "price": float(B["price"])},
                "C": C_data,
            },
            "wait_zone": {"low": fib[0.6], "high": fib[0.7]},
            "historical_bars_used": len(df),
            "bullish_divergence_confluence": confluence_indicator,  # None jika tidak ada, itu OK
        }

        # Cari Konfirmasi Pertama di zona tersebut, dibatasi confirmation_window
        window = int(_resolve_timeframe_param(cfg, "confirmation_window", timeframe))
        entry_idx = None
        search_end = min(pattern_candle_index + 1 + window, len(df))
        for i in range(pattern_candle_index + 1, search_end):
            if is_confirmation_candle(df, i):
                # Entry harus tetap di area value (tidak mengejar terlalu tinggi di atas zona koreksi)
                if df["Close"].iloc[i] <= fib[0.7] * 1.1:
                    entry_idx = i
                    break

        if entry_idx is None:
            return _waiting_result(self.name, symbol, timeframe, pattern_candle_index, base_metadata)

        tp_ext = calculate_fib_extension(A["price"], B["price"], C_data["price"], [1.618])
        tp_p = tp_ext[1.618]
        entry_p = float(df["Close"].iloc[entry_idx])
        sl_p = float(A["price"])  # invalidasi = low A (low bullish sebelumnya), sesuai materi Day 2

        if not (sl_p < entry_p < tp_p):
            return None
        rr = (tp_p - entry_p) / (entry_p - sl_p) if (entry_p - sl_p) > 0 else 0.0
        if rr < cfg["min_risk_reward"]:
            return None

        base_metadata.update({"tp_extension": tp_ext})

        return SetupResult(
            status=SignalStatus.READY,
            strategy_name=self.name,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=entry_p,
            stop_loss=sl_p,
            take_profit=tp_p,
            risk_reward=rr,
            pattern_candle_index=pattern_candle_index,
            entry_candle_index=entry_idx,
            metadata=base_metadata,
        )


# ==============================================================================
# STRATEGY: HIDDEN BULLISH DIVERGENCE (ABCDE)
# ==============================================================================
# Implementasi ASLI (bukan sekadar inherit CorrectionStrategy seperti versi
# lama). Sesuai materi Day 2:
# - Butuh continuous pattern (segitiga/"sempa") berlabel A-B-C-D dulu.
# - Harga naik (D > B, higher-high) TAPI indikator turun (lower-high) -> hidden.
# - Titik E dicari via Fibonacci retracement 0.6-0.7 dari C(low)->D(high).
# - Entry di candle konfirmasi setelah E.
# - SL = low A (BUKAN low C, BUKAN low E).
# - TP = proyeksi leg (E->D) dari E dengan level 1.2; level 1.0 (=D) WAJIB
#   ditembus dulu supaya tidak berakhir jadi double-top.
# ==============================================================================

class HiddenBullishDivergenceStrategy(BaseStrategy):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("Hidden Bullish Divergence (ABCDE)", config)

    def get_max_age(self, timeframe: str) -> int:
        return int(_resolve_timeframe_param(METHOD_CONFIG[self.name], "max_signal_age", timeframe))

    def evaluate(self, df: pd.DataFrame, pivots: pd.DataFrame, indicators: Dict[str, pd.Series]) -> Optional[SetupResult]:
        cfg = METHOD_CONFIG[self.name]
        if pivots.empty or len(df) < 20:
            return None

        symbol = df.attrs.get("symbol", "UNKNOWN")
        timeframe = df.attrs.get("timeframe", "UNKNOWN")

        # 1. Butuh continuation pattern A-B-C-D dulu (syarat mutlak sesuai materi Day 2)
        try:
            A = pivots[pivots["movement_label"] == "A"].iloc[-1]
            B = pivots[pivots["movement_label"] == "B"].iloc[-1]
            C = pivots[pivots["movement_label"] == "C"].iloc[-1]
            D = pivots[pivots["movement_label"] == "D"].iloc[-1]
        except (IndexError, KeyError):
            return None

        if not (A["index"] < B["index"] < C["index"] < D["index"]):
            return None
        # Struktur continuation naik: D harus higher-high dari B, C harus higher-low dari A
        if not (D["price"] > B["price"] and C["price"] > A["price"]):
            return None

        # 2. Verifikasi HIDDEN divergence: harga naik (D>B) TAPI indikator turun (lower-high)
        confirming_indicator = _first_confirming_indicator(
            indicators, int(B["index"]), int(D["index"]), expect_higher_at_late=False
        )
        if confirming_indicator is None:
            return None

        # 3. Cari titik E via Fibonacci retracement 0.6-0.7 dari C(low) -> D(high)
        #    (memakai konvensi calculate_fib_levels yang SAMA dengan CorrectionStrategy
        #    yang sudah diaudit -- tidak membuat rumus fib kedua yang berbeda).
        fib = calculate_fib_levels(C["price"], D["price"], [0.6, 0.7])
        e_data = get_swing_low_since(df, int(D["index"]))
        if e_data is None:
            return None
        if not (fib[0.6] <= e_data["price"] <= fib[0.7] * 1.05):
            return None
        # E tidak boleh lebih rendah dari A (kalau sampai lebih rendah, ini sudah
        # bukan hidden lagi -- strukturnya invalid sejak awal)
        if not (e_data["price"] > A["price"]):
            return None

        pattern_candle_index = int(e_data["idx"])

        base_metadata = {
            "pivots": {
                "A": {"idx": int(A["index"]), "price": float(A["price"])},
                "B": {"idx": int(B["index"]), "price": float(B["price"])},
                "C": {"idx": int(C["index"]), "price": float(C["price"])},
                "D": {"idx": int(D["index"]), "price": float(D["price"])},
                "E": e_data,
            },
            "indicator": confirming_indicator,
            "e_zone": fib,
            "historical_bars_used": len(df),
        }

        # 4. Cari candle konfirmasi setelah E, dibatasi confirmation_window
        window = int(_resolve_timeframe_param(cfg, "confirmation_window", timeframe))
        entry_idx = find_confirmation_candle(df, pattern_candle_index, window)

        if entry_idx is None:
            return _waiting_result(self.name, symbol, timeframe, pattern_candle_index, base_metadata)

        entry_p = float(df["Close"].iloc[entry_idx])
        sl_p = float(A["price"])  # invalidasi WAJIB di low A, bukan low C / low E (materi Day 2)

        # 5. TP: proyeksi leg (E->D) dari E dengan level 1.0 (=D, syarat breakout) dan 1.2 (target)
        tp_fib = calculate_fib_levels(e_data["price"], D["price"], [1.0, 1.2])
        breakout_level = tp_fib[1.0]  # harus ditembus dulu (~ level D) sesuai materi
        tp_p = tp_fib[1.2]

        if not (sl_p < entry_p < tp_p):
            return None
        rr = (tp_p - entry_p) / (entry_p - sl_p) if (entry_p - sl_p) > 0 else 0.0
        if rr < cfg["min_risk_reward"]:
            return None

        base_metadata.update({
            "tp_fib": tp_fib,
            "requires_breakout_level": breakout_level,
            "breakout_note": (
                "Entry di E tetap valid walau belum breakout. Target 1.2 baru realistis "
                "setelah harga menembus breakout_level (~level D); jika gagal breakout, "
                "risiko berubah jadi double-top ('dot top')."
            ),
        })

        return SetupResult(
            status=SignalStatus.READY,
            strategy_name=self.name,
            symbol=symbol,
            timeframe=timeframe,
            entry_price=entry_p,
            stop_loss=sl_p,
            take_profit=tp_p,
            risk_reward=rr,
            pattern_candle_index=pattern_candle_index,
            entry_candle_index=entry_idx,
            metadata=base_metadata,
        )
