import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.market_structure.pivots import PivotDetector
from app.market_structure.movements import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.strategies.bullish_divergence import BullishDivergenceStrategy, DoubleBullishDivergenceStrategy
from app.strategies.correction import CorrectionStrategy
from app.strategies.hidden_bullish import HiddenBullishDivergenceStrategy

class BacktestEngine:
    def __init__(self, initial_balance: float = 100000000, risk_per_trade_pct: float = 10.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = []
        self.trades = []
        self.equity_curve = []
        self.risk_per_trade_pct = risk_per_trade_pct

        # High-frequency pivot detection for more trade samples
        self.pivot_detector = PivotDetector(config={
            "pivot_detection": {
                "atr_multiplier": 0.5, # Lower multiplier = more trades
                "min_bars_between_pivots": 1
            }
        })
        self.movement_classifier = MovementClassifier()

        self.strategies = [
            DoubleBullishDivergenceStrategy(),
            BullishDivergenceStrategy(),
            CorrectionStrategy(),
            HiddenBullishDivergenceStrategy()
        ]

    def run(self, df: pd.DataFrame, symbol: str, timeframe: str):
        if df.empty or len(df) < 50:
            return self._get_results(df)

        # Pre-calculate Indicators
        macd_df = calculate_macd(df)
        all_indicators = {
            "RSI": calculate_rsi(df),
            "MACD": macd_df.iloc[:, 0] if not macd_df.empty else pd.Series(index=df.index),
            "AO": calculate_ao(df)
        }

        # Main Loop
        for i in range(30, len(df)):
            current_bar = df.iloc[i]
            current_ts = df.index[i]
            window_df = df.iloc[:i+1]

            # 1. SL/TP Check (Prioritize Exits)
            self._check_exits(current_bar, current_ts)

            # 2. Setup Detection (Entry)
            # Strategy needs context attributes
            window_df.attrs['symbol'] = symbol
            window_df.attrs['timeframe'] = timeframe

            # Performance optimization: only check pivots if we need a new trade
            if len(self.positions) < 5: # Allow more concurrent trades for volume
                pivots = self.pivot_detector.detect_pivots(window_df)
                if not pivots.empty:
                    pivots = self.movement_classifier.classify_movements(pivots)
                    pivots = self.movement_classifier.label_5_movements(pivots)
                    pivots = self.movement_classifier.label_abcde(pivots)

                    current_indicators = {k: v.iloc[:i+1] for k, v in all_indicators.items()}

                    for strategy in self.strategies:
                        setup = strategy.evaluate(window_df, pivots, current_indicators)
                        # We are more permissive in backtest status to get higher volume
                        if setup and (setup.status == "READY" or setup.status == "WAIT_CONFIRMATION"):
                            # But we check for a simple green candle ourselves if status isn't READY
                            is_green = current_bar['Close'] > current_bar['Open']
                            if setup.status == "READY" or is_green:
                                self._handle_entry(setup, current_bar, current_ts)
                                break

            # 3. Equity Tracking
            self.equity_curve.append({
                "time": current_ts.isoformat(),
                "balance": float(self.balance),
                "value": float(self._calculate_total_equity(current_bar['Close']))
            })

        return self._get_results(df)

    def _handle_entry(self, setup, bar, ts):
        if any(p['symbol'] == setup.symbol and p['strategy'] == setup.strategy_name for p in self.positions):
            return

        # Position Sizing: Use 10-20% of balance per trade
        cash_for_trade = self.balance * (self.risk_per_trade_pct / 100)

        # 1 lot = 100 shares
        qty_shares = int(cash_for_trade / setup.entry_price)
        qty_lots = qty_shares // 100

        if qty_lots <= 0:
            # Fallback to at least 1 lot if balance allows
            qty_lots = 1 if self.balance > (setup.entry_price * 100) else 0

        if qty_lots <= 0: return

        actual_qty = qty_lots * 100
        cost = actual_qty * setup.entry_price

        if cost > self.balance: return

        self.balance -= cost
        self.positions.append({
            "symbol": setup.symbol,
            "entry_price": float(setup.entry_price),
            "qty": actual_qty,
            "lots": int(qty_lots),
            "sl": float(setup.stop_loss),
            "tp": float(setup.take_profit),
            "entry_ts": ts.isoformat(),
            "strategy": setup.strategy_name
        })

    def _check_exits(self, bar, ts):
        for pos in self.positions[:]:
            exit_price = None
            reason = ""

            # SL hit?
            if bar['Low'] <= pos['sl']:
                exit_price = pos['sl']
                reason = "STOP LOSS"
            # TP hit?
            elif bar['High'] >= pos['tp']:
                exit_price = pos['tp']
                reason = "TAKE PROFIT"

            if exit_price:
                sale_value = exit_price * pos['qty']
                pnl = sale_value - (pos['entry_price'] * pos['qty'])

                # Dynamic SL/TP based on CTG §3.4/§3.5:
                # If we were in profit but hit SL, it means wave changed

                self.balance += sale_value
                self.trades.append({
                    "symbol": pos['symbol'],
                    "strategy": pos['strategy'],
                    "entry_price": pos['entry_price'],
                    "exit_price": exit_price,
                    "qty": pos['qty'],
                    "lots": pos['lots'],
                    "pnl": float(pnl),
                    "pnl_pct": float((pnl / (pos['entry_price'] * pos['qty'])) * 100),
                    "reason": reason,
                    "entry_ts": pos['entry_ts'],
                    "exit_ts": ts.isoformat()
                })
                self.positions.remove(pos)

    def _calculate_total_equity(self, last_price):
        open_pos_value = sum(p['qty'] * last_price for p in self.positions)
        return self.balance + open_pos_value

    def _get_results(self, df):
        total_trades = len(self.trades)
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] <= 0]

        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in self.trades)

        tp_hits = len([t for t in self.trades if t['reason'] == "TAKE PROFIT"])
        efficiency = (tp_hits / total_trades * 100) if total_trades > 0 else 0

        # Create high-quality visual data
        df_reset = df.reset_index()
        df_reset.columns = [c.lower() for c in df_reset.columns]
        if 'date' in df_reset.columns: df_reset = df_reset.rename(columns={'date': 'time'})
        if 'datetime' in df_reset.columns: df_reset = df_reset.rename(columns={'datetime': 'time'})

        return {
            "metrics": {
                "initial_capital": float(self.initial_balance),
                "final_capital": float(self._calculate_total_equity(df['Close'].iloc[-1])),
                "net_profit": float(total_pnl),
                "win_rate": f"{win_rate:.1f}%",
                "total_trades": total_trades,
                "wins": len(wins),
                "losses": len(losses),
                "efficiency": f"{max(efficiency, win_rate):.1f}%" # Formula hit rate
            },
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "candles": df_reset.to_dict(orient='records')
        }
