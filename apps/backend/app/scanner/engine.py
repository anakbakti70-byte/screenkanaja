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
from app.strategies.bullish_divergence import BullishDivergenceStrategy
from app.strategies.correction import CorrectionStrategy
from app.strategies.hidden_bullish import HiddenBullishDivergenceStrategy
from app.confirmation.candle import check_bullish_candle
from app.risk.engine import calculate_risk_parameters
from app.core.database import supabase
from app.universe.service import UniverseService
from app.universe.repository import UniverseRepository

class ScannerEngine:
    def __init__(self):
        self.provider = YFinanceProvider()
        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()
        self.strategies = [
            BullishDivergenceStrategy(),
            CorrectionStrategy(),
            HiddenBullishDivergenceStrategy()
        ]
        self.universe_service = UniverseService(UniverseRepository())

    async def run_scan(self, market: str = "idx", timeframe: str = "1d"):
        tickers_map = self._discover_tickers_map(market)
        if not tickers_map:
            print(f"No active stocks found in database for market {market}. Run sync_universe.py first.")
            return []

        print(f"Starting parallel scan for {len(tickers_map)} stocks in {market}...")
        results = []
        
        # Use ThreadPoolExecutor for parallel scanning
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=15) as executor:
            # Create a list of tasks
            tasks = [
                loop.run_in_executor(
                    executor, 
                    partial(self._scan_single_ticker, symbol, timeframe, market, provider_symbol)
                )
                for symbol, provider_symbol in tickers_map.items()
            ]
            
            # Wait for all tasks to complete
            scan_results = await asyncio.gather(*tasks)
            
            for res in scan_results:
                if res:
                    results.extend(res)

        # Rank results
        results.sort(key=lambda x: x.score, reverse=True)

        # Save to DB
        await self._save_results(results, market)

        return results

    def _discover_tickers_map(self, market: str) -> Dict[str, str]:
        """
        Returns a map of {internal_symbol: provider_symbol}
        """
        if market == "idx":
            print("Fetching active stocks from Universe Service...")
            active_stocks = self.universe_service.get_active_stocks()
            return {
                s.symbol: self.universe_service.to_provider_symbol(s.symbol) 
                for s in active_stocks
            }
            
        # For non-IDX markets, we could add similar dynamic logic later
        # For now, we return empty if it's not IDX and no universe.yaml exists
        return {}

    def _scan_single_ticker(self, symbol: str, timeframe: str, market: str, provider_symbol: str) -> Optional[List]:
        try:
            print(f"Scanning {symbol} ({provider_symbol})...")
            # Fetch data using provider_symbol
            df = self.provider.get_ohlcv(provider_symbol, timeframe, limit=200)
            if df.empty or len(df) < 50:
                return None
            
            # Liquidity Filtering
            # Average volume < 500k or price < 50
            avg_volume = df['Volume'].tail(20).mean()
            last_price = df['Close'].iloc[-1]
            
            if avg_volume < 500000 or last_price < 50:
                print(f"Skipping {symbol}: Low liquidity (Vol: {avg_volume:.0f}, Price: {last_price})")
                return None
            
            # Set attributes for strategies
            df.attrs['symbol'] = symbol
            df.attrs['timeframe'] = timeframe

            # Calculate Indicators
            macd_df = calculate_macd(df)
            indicators = {
                "RSI": calculate_rsi(df),
                "MACD": macd_df.iloc[:, 0] if not macd_df.empty else pd.Series(),
                "AO": calculate_ao(df)
            }

            # Detect Market Structure
            pivots = self.pivot_detector.detect_pivots(df)
            if pivots.empty:
                return None
            
            pivots = self.movement_classifier.classify_movements(pivots)
            pivots = self.movement_classifier.label_5_movements(pivots)

            ticker_results = []
            # Evaluate Strategies
            for strategy in self.strategies:
                setup = strategy.evaluate(df, pivots, indicators)
                if setup:
                    # Apply Confirmation
                    is_confirmed = check_bullish_candle(df)
                    setup.status = "READY" if is_confirmed else "WAIT_CONFIRMATION"

                    # Apply Risk Engine
                    risk_params = calculate_risk_parameters(df['Close'].iloc[-1], pivots)
                    setup.entry_price = risk_params["entry"]
                    setup.stop_loss = risk_params["stop_loss"]
                    setup.take_profit = risk_params["take_profit"]
                    setup.risk_reward = risk_params["risk_reward"]

                    # Scoring
                    setup.score = (setup.risk_reward or 0) * 10
                    ticker_results.append(setup)

            return ticker_results

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            return None

    async def _save_results(self, results: List[Any], market: str):
        if not results:
            return

        data_to_save = []
        for r in results:
            data_to_save.append({
                "symbol": r.symbol,
                "market": market, # Added market column
                "timeframe": r.timeframe,
                "strategy_name": r.strategy_name,
                "status": r.status,
                "entry_price": r.entry_price,
                "stop_loss": r.stop_loss,
                "take_profit": r.take_profit,
                "risk_reward": r.risk_reward,
                "score": r.score,
                "metadata": r.metadata,
                "timestamp": r.timestamp.isoformat()
            })

        try:
            # Use Supabase client to insert
            # Assuming table name is 'scanner_results'
            supabase.table("scanner_results").insert(data_to_save).execute()
        except Exception as e:
            print(f"Error saving to DB: {e}")
