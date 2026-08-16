import math
import datetime as dt
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, time as dt_time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import partial

# Dependencies
from app.providers.yfinance_provider import YFinanceProvider
from app.market_structure.pivots import PivotDetector
from app.market_structure.movements import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.core.database import supabase
from app.core.llm import llm_service
from app.universe.service import UniverseService
from app.universe.repository import UniverseRepository

# Integrated Strategies (from the new combined file)
from app.strategies.technical_logic import (
    BullishDivergenceStrategy,
    DoubleBullishDivergenceStrategy,
    CorrectionStrategy,
    HiddenBullishDivergenceStrategy
)

# ==============================================================================
# CATATAN PERBAIKAN (tidak ada perubahan RUMUS di file ini -- semua bug
# Fibonacci ada di technical_logic.py dan sudah diperbaiki di sana).
#
# Yang penting untuk diketahui: SAFETY GUARD di _scan_single_ticker() di bawah
# ini ("TP > Entry > SL") sebelumnya secara diam-diam MENIMPA hasil TP/SL yang
# salah arah dari technical_logic.py lama dengan nilai default (entry*0.95
# untuk SL, entry + risk*2.0 untuk TP). Ini artinya bug arah Fibonacci di file
# strategi TIDAK MUNCUL sebagai TP<Entry atau SL>Entry yang jelas-jelas salah,
# tapi tetap menghasilkan level TP/SL yang SALAH SECARA NILAI (tidak sesuai
# rumus rulebook), meskipun lolos guard ini. Setelah technical_logic.py
# diperbaiki, guard ini seharusnya jauh lebih jarang ter-trigger -- kalau guard
# ini masih sering aktif setelah perbaikan, itu tanda ada bug lain di hulu
# (pivot detection / movement classifier) yang perlu diperiksa terpisah.
#
# Guard ini TETAP DIPERTAHANKAN sebagai pengaman terakhir (defensive
# programming), bukan karena rumusnya benar -- kalau guard ini aktif, nilai
# TP/SL yang dihasilkan TIDAK LAGI merepresentasikan rulebook (§3-§5), jadi
# sebaiknya sinyal dengan needs_guard=True difilter/ditandai terpisah agar
# tidak tercampur dengan sinyal yang murni dari kalkulasi rulebook.
# ==============================================================================

from app.core.market_utils import IDXCalendar, is_idx_market_open, Fees, is_ara, is_arb

# ==============================================================================
# PART 3: SCANNER ENGINE (Previously engine.py)
# ==============================================================================

class ScannerEngine:
    def __init__(self):
        self.provider = YFinanceProvider()
        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()
        self.strategies = [DoubleBullishDivergenceStrategy(), BullishDivergenceStrategy(),
                           CorrectionStrategy(), HiddenBullishDivergenceStrategy()]
        self.universe_service = UniverseService(UniverseRepository())

    async def run_scan(self, market: str = "idx", timeframe: str = "1d"):
        try:
            from app.market_structure.regime import MarketRegimeDetector
            await MarketRegimeDetector().update_market_regime()
            tickers_map = self._discover_tickers_map(market)
        except Exception as e:
            print(f"DATABASE ERROR: {e}"); return []
        if not tickers_map: return []

        print(f"Scanning {len(tickers_map)} stocks...")
        results = []
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=15) as executor:
            tasks = [loop.run_in_executor(executor, partial(self._scan_single_ticker, symbol, timeframe, market, ps))
                     for symbol, ps in tickers_map.items()]
            scan_results = await asyncio.gather(*tasks)
            for res in scan_results:
                if res: results.extend(res)
        results.sort(key=lambda x: x.score, reverse=True)
        await self._save_results(results, market)
        return results

    def _discover_tickers_map(self, market: str) -> Dict[str, str]:
        if market == "idx":
            return {s.symbol: self.universe_service.to_provider_symbol(s.symbol) for s in self.universe_service.get_active_stocks()}
        return {}

    def _scan_single_ticker(self, symbol: str, timeframe: str, market: str, provider_symbol: str) -> Optional[List]:
        try:
            df = self.provider.get_ohlcv(provider_symbol, timeframe, limit=200)
            if df.empty or len(df) < 50: return None
            last_price = float(df['Close'].iloc[-1])
            if timeframe == "1d":
                try: supabase.table("stock_master").update({"last_price": last_price}).eq("symbol", symbol).execute()
                except: pass
            if last_price > 1000: return None  # rulebook §1.3: currentPrice < 1000
            avg_volume = df['Volume'].tail(10).mean()
            if (last_price * avg_volume) < 1_000_000_000: return None  # proxy likuiditas rupiah, §1.3

            df.attrs['symbol'], df.attrs['timeframe'] = symbol, timeframe
            indicators = {"RSI": calculate_rsi(df), "AO": calculate_ao(df),
                          "MACD": calculate_macd(df).iloc[:, 0] if not calculate_macd(df).empty else pd.Series()}

            pivots = self.pivot_detector.detect_pivots(df)
            if pivots.empty: return None
            pivots = self.movement_classifier.classify_movements(pivots)
            pivots = self.movement_classifier.label_5_movements(pivots)
            pivots = self.movement_classifier.label_abcde(pivots)

            ticker_results = []
            for strategy in self.strategies:
                setup = strategy.evaluate(df, pivots, indicators)
                if setup:
                    # --- SAFETY GUARD (TP > Entry > SL) ---
                    # Ini adalah pengaman defensif TERAKHIR, bukan sumber rumus
                    # yang benar. Sejak technical_logic.py diperbaiki (lihat
                    # catatan di atas file ini), guard ini seharusnya jauh
                    # lebih jarang aktif. Kalau aktif, tandai agar tidak
                    # tercampur dengan sinyal murni hasil rulebook.
                    guard_triggered = False
                    if setup.stop_loss >= setup.entry_price:
                        setup.stop_loss = setup.entry_price * 0.95
                        guard_triggered = True
                    if setup.take_profit <= setup.entry_price:
                        risk = setup.entry_price - setup.stop_loss
                        setup.take_profit = setup.entry_price + (risk * 2.0)
                        guard_triggered = True
                    risk, reward = setup.entry_price - setup.stop_loss, setup.take_profit - setup.entry_price
                    setup.risk_reward = round(reward / risk, 2) if risk > 0 else 0

                    # --- CALENDAR CONTEXT ---
                    next_day = IDXCalendar.get_next_trading_day(datetime.now().date())
                    ctx = IDXCalendar.get_trading_context(datetime.combine(next_day, datetime.min.time()))
                    setup.metadata.update({"calendar": ctx, "week_info": f"Minggu ke-{ctx['week_number']}",
                                           "expected_entry_day": next_day.strftime('%A, %d %b %Y'),
                                           "safety_guard_triggered": guard_triggered})
                    ticker_results.append(setup)
            return ticker_results
        except Exception as e:
            print(f"Error scanning {symbol}: {e}"); return None

    async def _save_results(self, results: List[Any], market: str):
        if not results: return
        data = []
        for r in results:
            explanation = ""
            if r.status == "READY":
                try:
                    explanation = await llm_service.generate_explanation(signal_data={
                        "symbol": r.symbol, "strategy": r.strategy_name, "entry": r.entry_price, "sl": r.stop_loss,
                        "tp": r.take_profit, "rr": r.risk_reward, "timeframe": r.timeframe,
                        "prediksi_entri": r.metadata.get("expected_entry_day"),
                        "keterangan_waktu": r.metadata.get("week_info"), "status_pasar": r.metadata.get("calendar", {}).get("status")
                    })
                except: pass
            data.append({"symbol": r.symbol, "market": market, "timeframe": r.timeframe, "method": r.strategy_name,
                         "status": r.status, "entry_price": r.entry_price, "stop_loss": r.stop_loss,
                         "tp_short": r.take_profit, "tp_far": getattr(r, 'tp_far', None), "risk_reward": r.risk_reward,
                         "indicator_used": r.metadata.get("indicator_used", "Unknown"), "score": r.score,
                         "metadata": {**r.metadata, "explanation": explanation}, "created_at": r.timestamp.isoformat()})
        try: supabase.table("divergence_signal").upsert(data, on_conflict="symbol,method,timeframe").execute()
        except Exception as e: print(f"Error saving: {e}")