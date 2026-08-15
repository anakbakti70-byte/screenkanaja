import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import uuid

from app.market_structure.pivots import PivotDetector
from app.market_structure.movements import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.strategies.bullish_divergence import BullishDivergenceStrategy, DoubleBullishDivergenceStrategy
from app.strategies.correction import CorrectionStrategy
from app.strategies.hidden_bullish import HiddenBullishDivergenceStrategy
from app.utils.market import round_to_tick, is_ara, is_arb, Fees, apply_fees_and_slippage, LOT
from app.core.database import supabase

class BacktestEngine:
    def __init__(self, initial_balance: float = 100000000, risk_per_trade_pct: float = 1.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fees = Fees()

        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()

        self.strategies = [
            DoubleBullishDivergenceStrategy(),
            BullishDivergenceStrategy(),
            CorrectionStrategy(),
            HiddenBullishDivergenceStrategy()
        ]

    def run(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Main execution loop for backtesting a single symbol.
        Strictly follows final.md for entry/exit and lookahead prevention.
        """
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data"}

        # Calculate all indicators once for the whole series (deterministic)
        macd_df = calculate_macd(df)
        all_indicators = {
            "RSI": calculate_rsi(df),
            "MACD": macd_df['macd'] if not macd_df.empty else pd.Series(index=df.index),
            "AO": calculate_ao(df)
        }

        trades = []
        equity_curve = []
        positions = []
        unfilled_ara = 0

        # We start from bar 30 to ensure indicators and pivots have enough history
        for i in range(30, len(df) - 1):
            current_bar = df.iloc[i]
            next_bar = df.iloc[i+1] # Entry/Exit happen on next bar Open
            ts = df.index[i]

            # 1. Check Exits for open positions
            # Conservative logic: If SL and TP hit on same bar, assume SL first.
            for pos in positions[:]:
                exit_price = None
                reason = ""

                # Use current_bar for exit triggers
                if current_bar['Low'] <= pos['sl']:
                    exit_price = min(current_bar['Open'], pos['sl']) # Gap down handled
                    reason = "STOP LOSS"
                elif current_bar['High'] >= pos['tp']:
                    exit_price = pos['tp']
                    reason = "TAKE PROFIT"

                if exit_price:
                    # Check ARB (cannot sell on ARB)
                    prev_close = df.iloc[i-1]['Close']
                    if is_arb(exit_price, prev_close):
                        # Postpone exit to next bar
                        continue

                    self._execute_exit(pos, exit_price, reason, ts, trades, positions)

            # 2. Check Entries
            # Look only at data up to current_bar (no lookahead)
            if len(positions) == 0: # One position at a time for simplicity in this engine
                window_df = df.iloc[:i+1]
                window_df.attrs['symbol'] = symbol
                window_df.attrs['timeframe'] = timeframe

                pivots = self.pivot_detector.detect_pivots(window_df)
                if not pivots.empty:
                    pivots = self.movement_classifier.classify_movements(pivots)
                    pivots = self.movement_classifier.label_5_movements(pivots)
                    pivots = self.movement_classifier.label_abcde(pivots)

                    curr_inds = {k: v.iloc[:i+1] for k, v in all_indicators.items()}

                    for strategy in self.strategies:
                        setup = strategy.evaluate(window_df, pivots, curr_inds)
                        if setup and setup.status == "READY":
                            # Sinyal pada close T dieksekusi pada open T+1
                            entry_price_raw = next_bar['Open']
                            prev_close = current_bar['Close']

                            # Check ARA (cannot buy on ARA)
                            if is_ara(entry_price_raw, prev_close):
                                unfilled_ara += 1
                                break

                            self._execute_entry(setup, entry_price_raw, df.index[i+1], positions)
                            break

            # 3. Track Equity
            total_val = self.balance + sum(p['qty'] * current_bar['Close'] for p in positions)
            equity_curve.append({"time": ts.isoformat(), "value": float(total_val)})

        return self._summarize(trades, equity_curve, unfilled_ara, symbol, timeframe)

    def _execute_entry(self, setup, price_raw, ts, positions):
        entry_price = apply_fees_and_slippage(price_raw, "buy", self.fees)

        # Risk-based position sizing (§3.7)
        risk_per_share = abs(entry_price - setup.stop_loss)
        if risk_per_share == 0: return

        risk_amount = self.balance * (self.risk_per_trade_pct / 100)
        qty_shares = int(risk_amount / risk_per_share)
        qty_lots = qty_shares // LOT

        if qty_lots <= 0: return

        actual_qty = qty_lots * LOT
        cost = actual_qty * entry_price

        if cost > self.balance:
            # Try reducing lots
            qty_lots = int(self.balance // (entry_price * LOT))
            if qty_lots <= 0: return
            actual_qty = qty_lots * LOT
            cost = actual_qty * entry_price

        self.balance -= cost
        positions.append({
            "symbol": setup.symbol,
            "strategy": setup.strategy_name,
            "qty": actual_qty,
            "entry_price": entry_price,
            "sl": setup.stop_loss,
            "tp": setup.take_profit,
            "entry_ts": ts.isoformat(),
            "risk_amount": risk_amount
        })

    def _execute_exit(self, pos, price_raw, reason, ts, trades, positions):
        exit_price = apply_fees_and_slippage(price_raw, "sell", self.fees)
        sale_value = exit_price * pos['qty']

        pnl = sale_value - (pos['entry_price'] * pos['qty'])
        r_multiple = pnl / pos['risk_amount'] if pos['risk_amount'] > 0 else 0

        self.balance += sale_value
        trades.append({
            "symbol": pos['symbol'],
            "strategy": pos['strategy'],
            "entry_price": pos['entry_price'],
            "exit_price": exit_price,
            "qty": pos['qty'],
            "pnl": float(pnl),
            "r_multiple": float(r_multiple),
            "reason": reason,
            "entry_ts": pos['entry_ts'],
            "exit_ts": ts.isoformat()
        })
        positions.remove(pos)

    def _summarize(self, trades, equity_curve, unfilled_ara, symbol, timeframe):
        if not trades:
            return {"metrics": {"total_trades": 0, "unfilled_ara": unfilled_ara}, "trades": [], "equity_curve": equity_curve}

        df_trades = pd.DataFrame(trades)
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]

        win_rate = len(wins) / len(trades) * 100
        expectancy = df_trades['r_multiple'].mean()

        gross_profit = wins['pnl'].sum()
        gross_loss = abs(losses['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Drawdown calculation
        equity_vals = [e['value'] for e in equity_curve]
        peak = np.maximum.accumulate(equity_vals)
        drawdown = (equity_vals / peak) - 1
        max_dd = drawdown.min() * 100

        results = {
            "metrics": {
                "total_trades": len(trades),
                "win_rate": f"{win_rate:.1f}%",
                "expectancy": round(float(expectancy), 3),
                "profit_factor": round(float(profit_factor), 2),
                "max_drawdown": f"{max_dd:.1f}%",
                "unfilled_ara": unfilled_ara,
                "net_profit": float(df_trades['pnl'].sum())
            },
            "trades": trades,
            "equity_curve": equity_curve
        }

        # PHASE 11: Save to Database if required
        self._save_to_db(results, symbol, timeframe)

        return results

    def _save_to_db(self, results, symbol, timeframe):
        try:
            # Insert Backtest Run
            run_data = {
                "strategy": "Multi-Strategy Portfolio",
                "symbol": symbol,
                "timeframe": timeframe,
                "trade_count": results['metrics']['total_trades'],
                "win_rate": float(results['metrics']['win_rate'].replace('%', '')),
                "expectancy": results['metrics']['expectancy'],
                "profit_factor": results['metrics']['profit_factor'],
                "max_drawdown": float(results['metrics']['max_drawdown'].replace('%', '')),
                "verdict": "PROVEN_POSITIVE" if results['metrics']['expectancy'] > 0 else "NEGATIVE_EXPECTANCY"
            }
            resp = supabase.table("backtest_runs").insert(run_data).execute()
            if resp.data:
                run_id = resp.data[0]['id']
                # Batch insert trades
                trades_data = []
                for t in results['trades']:
                    trades_data.append({
                        "run_id": run_id,
                        "symbol": t['symbol'],
                        "strategy": t['strategy'],
                        "entry_date": t['entry_ts'],
                        "exit_date": t['exit_ts'],
                        "entry_price": t['entry_price'],
                        "exit_price": t['exit_price'],
                        "net_pnl": t['pnl'],
                        "r_multiple": t['r_multiple'],
                        "exit_reason": t['reason']
                    })
                if trades_data:
                    supabase.table("backtest_trades").insert(trades_data).execute()
        except Exception as e:
            print(f"Error saving backtest to DB: {e}")
