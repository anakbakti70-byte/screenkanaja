"""
==============================================================================
SCANNER_CORE.PY — ORCHESTRATOR (ACTIONABLE ENTRY ENGINE)
==============================================================================
Perbaikan Total (Fix Issue 1-4 & Masalah Tersisa):
1. WAITING_CONFIRMATION Persistence: Sinyal yang menunggu konfirmasi di-load
   kembali dari DB dan dicek apakah "cendol" sudah muncul di candle terbaru.
2. Real-time Re-validation: Setiap siklus scan, SEMUA sinyal aktif (READY/VALID)
   dievaluasi ulang menggunakan validate_signal_freshness(). Sinyal otomatis
   menjadi STALE jika umur bertambah atau harga lari terlalu jauh.
3. Duplicate Prevention: Menggunakan pattern_candle_index untuk memastikan
   satu pola yang sama tidak dideteksi berulang kali sebagai sinyal baru.
4. Granular Persistence: Upsert sekarang menggunakan kombinasi unik
   (symbol, method, timeframe, pattern_idx, entry_idx) agar history pattern
   tidak saling menimpa.
5. Automated Fixes for Remaining Issues:
   - Fixed missing imports (_resolve_timeframe_param, calculate_fib_extension).
   - Implemented strategy-specific target recalculation (_recalculate_setup_targets).
   - Synchronized DB states with current scan results (_sync_db_states).
   - Fixed entry_candle_index logic for WAITING_CONFIRMATION signals.
==============================================================================
"""

import math
import datetime as dt
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, time as dt_time
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import partial

# --- Core Market Rules (Source of Truth in market_utils.py) ---
from app.core.market_utils import (
    TickRegime, TICK_REGIMES, Fees, tick_size, round_to_tick
)

# Export LOT and HARGA_MIN for compatibility
LOT, HARGA_MIN = 100, 50

class IDXCalendar:
    """Indonesian Stock Exchange (IDX) Calendar Utility 2023 - 2026."""
    HOLIDAYS_2023 = [dt.date(2023, 1, 1), dt.date(2023, 1, 2), dt.date(2023, 1, 22), dt.date(2023, 1, 23),
                     dt.date(2023, 2, 18), dt.date(2023, 3, 22), dt.date(2023, 3, 23), dt.date(2023, 4, 7),
                     dt.date(2023, 4, 19), dt.date(2023, 4, 20), dt.date(2023, 4, 21), dt.date(2023, 4, 24),
                     dt.date(2023, 4, 25), dt.date(2023, 5, 1), dt.date(2023, 5, 18), dt.date(2023, 6, 1),
                     dt.date(2023, 6, 2), dt.date(2023, 6, 4), dt.date(2023, 6, 28), dt.date(2023, 6, 29),
                     dt.date(2023, 6, 30), dt.date(2023, 7, 19), dt.date(2023, 8, 17), dt.date(2023, 9, 28),
                     dt.date(2023, 12, 25), dt.date(2023, 12, 26)]

    HOLIDAYS_2024 = [dt.date(2024, 1, 1), dt.date(2024, 2, 8), dt.date(2024, 2, 9), dt.date(2024, 2, 10),
                     dt.date(2024, 2, 14), dt.date(2024, 3, 11), dt.date(2024, 3, 12), dt.date(2024, 3, 29),
                     dt.date(2024, 4, 8), dt.date(2024, 4, 9), dt.date(2024, 4, 10), dt.date(2024, 4, 11),
                     dt.date(2024, 4, 12), dt.date(2024, 4, 15), dt.date(2024, 5, 1), dt.date(2024, 5, 9),
                     dt.date(2024, 5, 10), dt.date(2024, 5, 23), dt.date(2024, 5, 24), dt.date(2024, 6, 1),
                     dt.date(2024, 6, 17), dt.date(2024, 6, 18), dt.date(2024, 7, 7), dt.date(2024, 8, 17),
                     dt.date(2024, 9, 16), dt.date(2024, 12, 25), dt.date(2024, 12, 26)]

    HOLIDAYS_2025 = [dt.date(2025, 1, 1), dt.date(2025, 1, 27), dt.date(2025, 1, 28), dt.date(2025, 1, 29),
                     dt.date(2025, 3, 28), dt.date(2025, 3, 29), dt.date(2025, 3, 31), dt.date(2025, 4, 1),
                     dt.date(2025, 4, 2), dt.date(2025, 4, 3), dt.date(2025, 4, 4), dt.date(2025, 4, 7),
                     dt.date(2025, 4, 18), dt.date(2025, 5, 1), dt.date(2025, 5, 12), dt.date(2025, 5, 13),
                     dt.date(2025, 5, 29), dt.date(2025, 5, 30), dt.date(2025, 6, 1), dt.date(2025, 6, 6),
                     dt.date(2025, 6, 9), dt.date(2025, 6, 27), dt.date(2025, 8, 17), dt.date(2025, 9, 5),
                     dt.date(2025, 12, 25), dt.date(2025, 12, 26)]

    ALL_HOLIDAYS = sorted(list(set(HOLIDAYS_2023 + HOLIDAYS_2024 + HOLIDAYS_2025)))

    @classmethod
    def is_holiday(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None: date_val = datetime.now().date()
        return date_val in cls.ALL_HOLIDAYS

    @classmethod
    def is_trading_day(cls, date_val: Optional[dt.date] = None) -> bool:
        if date_val is None: date_val = datetime.now().date()
        return date_val.weekday() < 5 and not cls.is_holiday(date_val)

    @classmethod
    def get_next_trading_day(cls, start_date: dt.date) -> dt.date:
        next_day = start_date + dt.timedelta(days=1)
        while not cls.is_trading_day(next_day): next_day += dt.timedelta(days=1)
        return next_day

def is_idx_market_open() -> bool:
    """
    Exact IDX schedule (WIB/GMT+7):
    Mon-Thu: 09:00-12:00, 13:30-15:49 (S1, S2), 15:50-15:59 (Pre-closing)
    Fri: 09:00-11:30, 14:00-15:49 (S1, S2), 15:50-15:59 (Pre-closing)
    """
    now = datetime.now(timezone(dt.timedelta(hours=7)))
    day, current_time = now.weekday(), now.time()

    if not IDXCalendar.is_trading_day(now.date()):
        return False

    # Monday - Thursday
    if day <= 3:
        s1 = (dt_time(9, 0), dt_time(12, 0))
        s2 = (dt_time(13, 30), dt_time(15, 59)) # Combine S2 and Pre-closing
        return (s1[0] <= current_time <= s1[1]) or (s2[0] <= current_time <= s2[1])

    # Friday
    elif day == 4:
        s1 = (dt_time(9, 0), dt_time(11, 30))
        s2 = (dt_time(14, 0), dt_time(15, 59)) # Combine S2 and Pre-closing
        return (s1[0] <= current_time <= s1[1]) or (s2[0] <= current_time <= s2[1])

    return False

# ==============================================================================
# PART 1: DEPENDENCIES
# ==============================================================================

# Dependencies
from app.providers.yfinance_provider import YFinanceProvider
from app.market_structure.pivots import PivotDetector
from app.market_structure.movements import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.core.database import supabase
from app.universe.service import UniverseService
from app.universe.repository import UniverseRepository

from app.strategies.base import SetupResult
from app.strategies.technical_logic import (
    BullishDivergenceStrategy,
    DoubleBullishDivergenceStrategy,
    CorrectionStrategy,
    HiddenBullishDivergenceStrategy,
    SignalStatus,
    METHOD_CONFIG,
    calculate_atr,
    validate_signal_freshness,
    find_confirmation_candle,
    calculate_fib_levels,
    calculate_fib_extension,
    _resolve_timeframe_param
)

# ==============================================================================
# PART 2: SCANNER ENGINE
# ==============================================================================

class ScannerEngine:
    def __init__(self):
        self.provider = YFinanceProvider()
        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()
        self.strategies = [
            DoubleBullishDivergenceStrategy(None),
            BullishDivergenceStrategy(None),
            CorrectionStrategy(None),
            HiddenBullishDivergenceStrategy(None)
        ]
        self.universe_service = UniverseService(UniverseRepository())

    async def run_scan(self, market: str = "idx", timeframe: str = "1d"):
        tickers = self.universe_service.get_active_stocks()
        if not tickers: return []

        print(f"🔍 SCANNING MARKET ({timeframe}) - 1s ACTIONABLE CYCLE...")

        # 1. Fetch active signals from DB for re-validation and confirmation tracking
        active_db_signals = await self._fetch_active_signals(market, timeframe)

        # 2. Run detection & validation on all tickers
        all_results = []
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = [
                loop.run_in_executor(executor, partial(self._scan_ticker, t.symbol, timeframe, active_db_signals.get(t.symbol, [])))
                for t in tickers
            ]
            scan_results = await asyncio.gather(*tasks)
            for res in scan_results:
                if res: all_results.extend(res)

        # 3. Cleanup DB: Mark signals that disappeared or turned STALE/INVALID
        await self._sync_db_states(market, timeframe, all_results)

        # 4. Background Broker Execution: Sync SL/TP for all active sessions
        # Ini memastikan SL/TP terjual otomatis meskipun user tidak membuka browser.
        await self._run_background_broker_sync()

        # 5. Save results (Upsert all)
        if all_results:
            await self._save_results(all_results, market)

        # 5. Return only READY/VALID for the active screening dashboard
        return [r for r in all_results if r.status in (SignalStatus.READY, SignalStatus.VALID)]

    async def _fetch_active_signals(self, market: str, timeframe: str) -> Dict[str, List[Dict]]:
        """Loads signals that need monitoring (WAITING, READY, VALID)."""
        try:
            res = supabase.table("divergence_signal") \
                .select("*") \
                .eq("market", market) \
                .eq("timeframe", timeframe) \
                .in_("status", [SignalStatus.WAITING_CONFIRMATION, SignalStatus.READY, SignalStatus.VALID]) \
                .execute()

            data = {}
            for r in res.data:
                sym = r['symbol']
                if sym not in data: data[sym] = []
                data[sym].append(r)
            return data
        except Exception as e:
            print(f"⚠️ Fetch active signals error: {e}")
            return {}

    def _scan_ticker(self, symbol: str, timeframe: str, existing_signals: List[Dict]) -> Optional[List[SetupResult]]:
        try:
            df = self.provider.get_ohlcv(symbol, timeframe, limit=200)
            if df.empty or len(df) < 50: return None

            df.attrs['symbol'], df.attrs['timeframe'] = symbol, timeframe
            current_price = float(df['Close'].iloc[-1])
            latest_idx = len(df) - 1

            indicators = {"AO": calculate_ao(df), "RSI": calculate_rsi(df), "MACD": calculate_macd(df)}
            atr_series = calculate_atr(df)
            atr_value = float(atr_series.iloc[-1]) if not atr_series.empty else None

            # Only detect pivots up to previous bar to avoid look-ahead bias
            pivots = self.pivot_detector.detect_pivots(df.iloc[:-1])
            if not pivots.empty:
                pivots = self.movement_classifier.classify_movements(pivots)
                pivots = self.movement_classifier.label_5_movements(pivots)
                pivots = self.movement_classifier.label_abcde(pivots)

            ticker_results = []

            # TRACKER: Avoid re-detecting patterns already in existing_signals
            processed_pattern_keys = { (s['method'], int(s['pattern_candle_index'])) for s in existing_signals }

            # --- PART A: Re-validate Existing Active Signals ---
            for s in existing_signals:
                # Re-construct SetupResult from DB record
                setup = SetupResult(
                    status=s['status'],
                    strategy_name=s['method'],
                    symbol=symbol,
                    timeframe=timeframe,
                    entry_price=float(s['entry_price']) if s['entry_price'] is not None else float('nan'),
                    stop_loss=float(s['stop_loss']) if s['stop_loss'] is not None else float('nan'),
                    take_profit=float(s['tp_short']) if s['tp_short'] is not None else float('nan'),
                    pattern_candle_index=int(s['pattern_candle_index']),
                    # Consistency Fix: if entry_candle_index was None/NaN, fallback to pattern_candle_index
                    entry_candle_index=int(s['entry_candle_index']) if s['entry_candle_index'] is not None else int(s['pattern_candle_index']),
                    metadata=s['metadata'] or {}
                )

                # Special Logic for WAITING_CONFIRMATION: Check for new confirmation candle
                if setup.status == SignalStatus.WAITING_CONFIRMATION:
                    cfg = METHOD_CONFIG.get(setup.strategy_name, METHOD_CONFIG["Bullish Divergence"])
                    window = int(_resolve_timeframe_param(cfg, "confirmation_window", timeframe))

                    found_idx = find_confirmation_candle(df, setup.pattern_candle_index, window)
                    if found_idx is not None:
                        # Update entry data
                        setup.entry_candle_index = found_idx
                        setup.entry_price = float(df["Close"].iloc[found_idx])
                        setup.stop_loss = float(df["Low"].iloc[found_idx])

                        # Recalculate TP based on strategy
                        setup = self._recalculate_setup_targets(setup, df)

                        # Mark as READY (will be validated below)
                        setup.status = SignalStatus.READY

                # Universal Validation (Age, Price Distance, Invalidation)
                cfg = METHOD_CONFIG.get(setup.strategy_name, METHOD_CONFIG["Bullish Divergence"])
                new_status, reason = validate_signal_freshness(setup, latest_idx, current_price, atr_value, cfg)

                setup.status = new_status
                setup.reason = reason
                setup.signal_age = latest_idx - setup.entry_candle_index

                if new_status == SignalStatus.VALID:
                    dist = (current_price - setup.entry_price) / setup.entry_price if setup.entry_price > 0 else 0
                    setup.reason = f"Signal masih valid. Age: {setup.signal_age} bar(s), Price distance: {dist:.2%}"

                setup.metadata.update({"current_price": current_price, "signal_age": setup.signal_age, "revalidated": True})

                ticker_results.append(setup)

            # --- PART B: Detect New Patterns ---
            for strategy in self.strategies:
                setup = strategy.evaluate(df, pivots, indicators)
                if setup:
                    # Check if this exact pattern is already known
                    if (setup.strategy_name, setup.pattern_candle_index) in processed_pattern_keys:
                        continue

                    # New pattern found! Validate it.
                    cfg = METHOD_CONFIG[strategy.name]
                    status, reason = validate_signal_freshness(setup, latest_idx, current_price, atr_value, cfg)
                    setup.status = status
                    setup.reason = reason
                    setup.signal_age = latest_idx - setup.entry_candle_index
                    setup.metadata.update({"current_price": current_price, "signal_age": setup.signal_age, "new_detection": True})

                    ticker_results.append(setup)

            return ticker_results
        except Exception:
            return None

    def _recalculate_setup_targets(self, setup: SetupResult, df: pd.DataFrame) -> SetupResult:
        """Recalculate TP/SL for a setup that just got confirmed."""
        if setup.strategy_name == "Bullish Divergence":
            p = setup.metadata.get("pivots", {})
            w5, w4 = p.get("W5", {}), p.get("W4", {})
            if w5 and w4:
                setup.take_profit = calculate_fib_levels(w5['price'], w4['price'], [0.6])[0.6]

        elif setup.strategy_name == "Double Bullish Divergence":
            # TP pendek: 0.6 dari leg (L2 -> rally_high)
            l2_price = setup.metadata.get("l2", {}).get("price")
            rally_high = setup.metadata.get("rally_high")
            if l2_price and rally_high:
                setup.take_profit = calculate_fib_levels(l2_price, rally_high, [0.6])[0.6]

        elif setup.strategy_name == "Correction (ABC)":
            p = setup.metadata.get("pivots", {})
            A, B, C = p.get("A", {}), p.get("B", {}), p.get("C", {})
            if A and B and C:
                setup.take_profit = calculate_fib_extension(A['price'], B['price'], C['price'], [1.618])[1.618]

        elif setup.strategy_name == "Hidden Bullish Divergence (ABCDE)":
            p = setup.metadata.get("pivots", {})
            E, D = p.get("E", {}), p.get("D", {})
            if E and D:
                setup.take_profit = calculate_fib_levels(E['price'], D['price'], [1.2])[1.2]

        return setup

    async def _sync_db_states(self, market: str, timeframe: str, current_results: List[SetupResult]):
        """Mark signals that are no longer detected as STALE."""
        try:
            # Ambil semua sinyal aktif dari DB
            res = supabase.table("divergence_signal") \
                .select("signal_id, symbol, method, pattern_candle_index, entry_candle_index, status") \
                .eq("market", market) \
                .eq("timeframe", timeframe) \
                .in_("status", [SignalStatus.WAITING_CONFIRMATION, SignalStatus.READY, SignalStatus.VALID]) \
                .execute()

            if not res.data:
                return

            # Buat set signal_id dari current_results
            current_ids = set()
            for r in current_results:
                # Consistent signal_id generation
                entry_idx = r.entry_candle_index if r.status != SignalStatus.WAITING_CONFIRMATION else r.pattern_candle_index
                sid = f"{r.symbol}:{r.strategy_name}:{r.timeframe}:{r.pattern_candle_index}:{entry_idx}"
                current_ids.add(sid)

            # Tandai yang tidak ada di current_results sebagai STALE
            for row in res.data:
                sid = row.get('signal_id')
                if not sid: continue # Skip data sampah tanpa ID

                if sid not in current_ids:
                    supabase.table("divergence_signal") \
                        .update({
                            "status": SignalStatus.STALE,
                            "reason": "Signal tidak lagi terdeteksi pada data terbaru (Pattern broken or disappeared)."
                        }) \
                        .eq("signal_id", sid) \
                        .execute()
                    print(f"🧹 Marked {sid} as STALE (not found in current scan)")

        except Exception as e:
            print(f"⚠️ Sync DB states error: {e}")

    async def _run_background_broker_sync(self):
        """Triggers SL/TP checks for all active backtest sessions."""
        try:
            from app.backtesting.virtual_broker import VirtualBroker
            # Ambil semua session ID yang aktif
            res = supabase.table("backtest_sessions").select("id").eq("status", "ACTIVE").execute()
            for session in res.data:
                broker = VirtualBroker(session["id"])
                broker.sync_positions_with_market()
        except Exception as e:
            print(f"⚠️ Background Broker Error: {e}")

    async def _save_results(self, results: List[SetupResult], market: str):
        if not results: return
        data = []

        def safe_nan(val):
            try:
                if val is None: return None
                f_val = float(val)
                return None if math.isnan(f_val) else f_val
            except: return None

        for r in results:
            # Generate unique signal_id
            # Consistency: if entry_candle_index is NaN (WAITING), use pattern_candle_index for unique identity
            is_waiting = r.status == SignalStatus.WAITING_CONFIRMATION
            entry_idx = r.entry_candle_index if not is_waiting else r.pattern_candle_index
            sid = f"{r.symbol}:{r.strategy_name}:{r.timeframe}:{r.pattern_candle_index}:{entry_idx}"

            data.append({
                "signal_id": sid,
                "symbol": r.symbol, "market": market, "timeframe": r.timeframe,
                "method": r.strategy_name, "status": r.status,
                "entry_price": safe_nan(r.entry_price),
                "stop_loss": safe_nan(r.stop_loss),
                "tp_short": safe_nan(r.take_profit),
                "risk_reward": safe_nan(r.risk_reward) or 0.0,
                "signal_age": r.signal_age, "reason": r.reason, "metadata": r.metadata,
                "pattern_candle_index": r.pattern_candle_index,
                "entry_candle_index": entry_idx,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        try:
            # Upsert using granular conflict target
            target = "symbol,method,timeframe,pattern_candle_index,entry_candle_index"
            supabase.table("divergence_signal").upsert(data, on_conflict=target).execute()
        except Exception as e:
            print(f"⚠️ Save results error: {e}")
