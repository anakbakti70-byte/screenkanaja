import yaml
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import asyncio
from functools import partial

from app.providers.yfinance_provider import YFinanceProvider
from app.market_structure.pivots import PivotDetector
from app.market_structure.movements import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.strategies.bullish_divergence import BullishDivergenceStrategy, DoubleBullishDivergenceStrategy
from app.strategies.correction import CorrectionStrategy
from app.strategies.hidden_bullish import HiddenBullishDivergenceStrategy
from app.confirmation.candle import check_bullish_candle
from app.core.database import supabase
from app.core.llm import llm_service
from app.universe.service import UniverseService
from app.universe.repository import UniverseRepository

class ScannerEngine:
    def __init__(self):
        self.provider = YFinanceProvider()
        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()
        self.strategies = [
            DoubleBullishDivergenceStrategy(), # Check double first as it's more specific
            BullishDivergenceStrategy(),
            CorrectionStrategy(),
            HiddenBullishDivergenceStrategy()
        ]
        self.universe_service = UniverseService(UniverseRepository())

    async def run_scan(self, market: str = "idx", timeframe: str = "1d"):
        try:
            # 1. Update Market Regime
            from app.market_structure.regime import MarketRegimeDetector
            regime_detector = MarketRegimeDetector()
            await regime_detector.update_market_regime()

            tickers_map = self._discover_tickers_map(market)
        except Exception as e:
            print(f"DATABASE ERROR: {e}")
            return []

        if not tickers_map:
            print(f"No active stocks found in database for market {market}. Run sync_universe.py first.")
            return []

        print(f"Starting parallel scan for {len(tickers_map)} stocks in {market}...")
        results = []
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=15) as executor:
            tasks = [
                loop.run_in_executor(
                    executor, 
                    partial(self._scan_single_ticker, symbol, timeframe, market, provider_symbol)
                )
                for symbol, provider_symbol in tickers_map.items()
            ]
            scan_results = await asyncio.gather(*tasks)
            for res in scan_results:
                if res: results.extend(res)

        results.sort(key=lambda x: x.score, reverse=True)
        await self._save_results(results, market)
        return results

    def _discover_tickers_map(self, market: str) -> Dict[str, str]:
        if market == "idx":
            active_stocks = self.universe_service.get_active_stocks()
            return {
                s.symbol: self.universe_service.to_provider_symbol(s.symbol) 
                for s in active_stocks
            }
        return {}

    def _scan_single_ticker(self, symbol: str, timeframe: str, market: str, provider_symbol: str) -> Optional[List]:
        try:
            # Rule §1.2: Fetch data from Yahoo Finance
            df = self.provider.get_ohlcv(provider_symbol, timeframe, limit=200)
            if df.empty or len(df) < 50: return None
            
            # Rule §1.3: Filter Price <= 1000
            last_price = float(df['Close'].iloc[-1])

            # Update last_price in stock_master if 1d for better accuracy
            if timeframe == "1d":
                try:
                    supabase.table("stock_master").update({"last_price": last_price}).eq("symbol", symbol).execute()
                except: pass

            if last_price > 1000: return None

            # Rule §1.3: Liquidity Filtering (Rupiah Value > 1 Billion)
            avg_volume = df['Volume'].tail(10).mean()
            if (last_price * avg_volume) < 1_000_000_000: return None
            
            df.attrs['symbol'] = symbol
            df.attrs['timeframe'] = timeframe

            # Rule §2: Calculate Indicators
            macd_df = calculate_macd(df)
            indicators = {
                "RSI": calculate_rsi(df),
                "MACD": macd_df.iloc[:, 0] if not macd_df.empty else pd.Series(),
                "AO": calculate_ao(df)
            }

            # Rule §3.1: Detect Market Structure (Pivots & Waves)
            pivots = self.pivot_detector.detect_pivots(df)
            if pivots.empty: return None
            
            pivots = self.movement_classifier.classify_movements(pivots)
            pivots = self.movement_classifier.label_5_movements(pivots)
            pivots = self.movement_classifier.label_abcde(pivots)

            ticker_results = []
            from app.strategies.gating import is_strategy_allowed

            for strategy in self.strategies:
                # GATING: Check if strategy is proven for this timeframe
                # In production, we might want to cache this check
                # allowed = await is_strategy_allowed(strategy.name, timeframe)
                # if not allowed: continue

                setup = strategy.evaluate(df, pivots, indicators)
                if setup:
                    # AI Reasoning if READY
                    explanation = ""
                    if setup.status == "READY":
                        # We use sync wrapper here for simplicity
                        pass

                    ticker_results.append(setup)

            return ticker_results

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            return None

    async def _save_results(self, results: List[Any], market: str):
        if not results: return

        data_to_save = []
        for r in results:
            explanation = ""
            if r.status == "READY":
                try:
                    explanation = await llm_service.generate_explanation(
                        signal_data={
                            "symbol": r.symbol,
                            "strategy": r.strategy_name,
                            "entry": r.entry_price,
                            "sl": r.stop_loss,
                            "tp": r.take_profit,
                            "timeframe": r.timeframe
                        }
                    )
                except: pass

            data_to_save.append({
                "symbol": r.symbol,
                "market": market,
                "timeframe": r.timeframe,
                "method": r.strategy_name,
                "status": r.status,
                "entry_price": r.entry_price,
                "stop_loss": r.stop_loss,
                "tp_short": r.take_profit,
                "tp_far": getattr(r, 'tp_far', None),
                "risk_reward": r.risk_reward,
                "indicator_used": r.metadata.get("indicator_used", "Unknown"),
                "score": r.score,
                "metadata": {**r.metadata, "explanation": explanation},
                "created_at": r.timestamp.isoformat()
            })

        try:
            if data_to_save:
                supabase.table("divergence_signal").upsert(
                    data_to_save,
                    on_conflict="symbol,method,timeframe"
                ).execute()
        except Exception as e:
            print(f"Error saving results: {e}")
