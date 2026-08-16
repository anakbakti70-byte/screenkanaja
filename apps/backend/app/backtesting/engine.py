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

class BacktestEngineV4:
    def __init__(self, initial_balance: float = 100000000, risk_per_trade_pct: float = 1.0):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
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
        Strictly follows Ajaib-style lot based sizing and dynamic TP/SL.
        """
        if df.empty or len(df) < 50:
            return {"error": "Insufficient data"}

        # Ensure index is sorted and unique
        df = df[~df.index.duplicated(keep='last')]
        df = df.sort_index()

        # Calculate all indicators once (deterministic)
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
        skipped_capital = 0
        skipped_risk_too_small = 0
        skipped_invalid_setup = 0
        blocked_arb_exits = 0

        # We start from bar 30 to ensure indicators and pivots have enough history
        for i in range(30, len(df) - 1):
            current_bar = df.iloc[i]
            next_bar = df.iloc[i+1]
            ts = df.index[i]
            next_ts = df.index[i+1]

            # 1. Check Exits for open positions (Market Order at Open of current bar if SL/TP hit on prev bar)
            # Actually, per requirements: Exit if current bar High >= TP or Low <= SL.
            for pos in positions[:]:
                exit_price = None
                reason = ""

                # Check SL
                if current_bar['Low'] <= pos['sl']:
                    # Gap down handled: if Open is already below SL, exit at Open
                    exit_price = min(current_bar['Open'], pos['sl'])
                    reason = "STOP LOSS"
                # Check TP
                elif current_bar['High'] >= pos['tp']:
                    # Gap up handled: if Open is already above TP, exit at Open
                    exit_price = max(current_bar['Open'], pos['tp'])
                    reason = "TAKE PROFIT"

                # Check Timeout (Max hold 20 bars if not specified otherwise)
                elif i - pos['entry_idx'] >= 20:
                    exit_price = current_bar['Close']
                    reason = "TIMEOUT"

                if exit_price is not None:
                    # Check ARB (cannot sell on ARB)
                    prev_close = df.iloc[i-1]['Close']
                    if is_arb(exit_price, prev_close):
                        # Postpone exit to next bar -- dicatat, bukan diam-diam
                        blocked_arb_exits += 1
                        continue

                    self._execute_exit(pos, exit_price, reason, ts, i, trades, positions)

            # 2. Check Entries
            if len(positions) == 0:
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
                            # Dynamic SL/TP are already in 'setup' from structure
                            entry_price_raw = next_bar['Open']
                            prev_close = current_bar['Close']

                            # Check ARA (cannot buy on ARA)
                            if is_ara(entry_price_raw, prev_close):
                                unfilled_ara += 1
                                break

                            entry_result = self._execute_entry(setup, entry_price_raw, next_ts, i+1, positions)
                            if entry_result == "invalid_setup":
                                skipped_invalid_setup += 1
                            elif entry_result == "risk_too_small":
                                skipped_risk_too_small += 1
                            elif entry_result in ("insufficient_capital", False):
                                skipped_capital += 1
                            break

            # 3. Track Equity
            open_pos_val = sum(p['qty'] * current_bar['Close'] for p in positions)
            total_equity = self.cash_balance + open_pos_val
            equity_curve.append({"time": int(ts.timestamp()), "value": float(total_equity)})

        skip_stats = {
            "unfilled_ara": unfilled_ara,
            "skipped_capital": skipped_capital,
            "skipped_risk_too_small": skipped_risk_too_small,
            "skipped_invalid_setup": skipped_invalid_setup,
            "blocked_arb_exits": blocked_arb_exits
        }
        return self._summarize(trades, equity_curve, skip_stats, symbol, timeframe, df, all_indicators)

    def _execute_entry(self, setup, price_raw, ts, idx, positions):
        # ============================================================
        # VALIDASI WAJIB (§3.4/§3.5/§4.3/§4.4/§5.3/§5.4 dokumen CTG):
        # Untuk setup long-only, urutan harga HARUS: SL < entry < TP.
        # Kalau modul strategi (pivot/fibonacci) menghasilkan level yang
        # keliru -- misalnya TP di bawah entry akibat data pivot basi --
        # engine akan menolak entry di sini, BUKAN membiarkan trade
        # aneh lolos lalu keluar dengan label TAKE PROFIT padahal rugi.
        # Ini adalah root-cause fix untuk bug "TP tapi PNL negatif".
        # ============================================================
        if setup.stop_loss is None or setup.take_profit is None:
            return "invalid_setup"
        if not (setup.stop_loss < price_raw < setup.take_profit):
            # Setup tidak valid secara struktur -- skip, jangan dipaksakan
            return "invalid_setup"

        # Apply fees to entry
        buy_fee_pct = self.fees.buy_pct

        # Position Sizing per Lot (100 shares)
        risk_rupiah = self.cash_balance * (self.risk_per_trade_pct / 100)
        jarak_sl = abs(price_raw - setup.stop_loss)

        if jarak_sl == 0: return "invalid_setup"

        lembar_ideal = risk_rupiah / jarak_sl
        jumlah_lot = int(np.floor(lembar_ideal / 100))

        if jumlah_lot <= 0:
            # Risiko per lot terlalu besar vs risk_rupiah yang dianggarkan
            # -- bukan kekurangan modal total, tapi 1 lot pun sudah
            # melebihi toleransi risiko. Dilaporkan terpisah dari
            # skipped_capital supaya user tahu ini soal ukuran risiko,
            # bukan soal saldo kas.
            return "risk_too_small"

        # Check capital
        total_buy_cost_raw = jumlah_lot * 100 * price_raw
        buy_fee = total_buy_cost_raw * buy_fee_pct
        total_required = total_buy_cost_raw + buy_fee

        if total_required > self.cash_balance:
            # Re-calculate max possible lots
            jumlah_lot = int(np.floor(self.cash_balance / (price_raw * 100 * (1 + buy_fee_pct))))
            if jumlah_lot <= 0:
                return "insufficient_capital"

            total_buy_cost_raw = jumlah_lot * 100 * price_raw
            buy_fee = total_buy_cost_raw * buy_fee_pct
            total_required = total_buy_cost_raw + buy_fee

        self.cash_balance -= total_required

        positions.append({
            "symbol": setup.symbol,
            "strategy": setup.strategy_name,
            "qty": jumlah_lot * 100,
            "lots": jumlah_lot,
            "entry_price": price_raw,
            "entry_fee": buy_fee,
            "sl": setup.stop_loss,
            "tp": setup.take_profit,
            "entry_ts": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            "entry_idx": idx,
            "risk_rupiah": risk_rupiah,
            "capital_used": total_buy_cost_raw
        })
        return "ok"

    def _execute_exit(self, pos, price_raw, reason, ts, current_idx, trades, positions):
        # Apply slippage and fees to exit
        exit_price_real = price_raw * (1 - self.fees.slippage_pct)
        sell_value_raw = exit_price_real * pos['qty']
        sell_fee = sell_value_raw * self.fees.sell_pct
        sell_value_net = sell_value_raw - sell_fee

        pnl_rp = sell_value_net - (pos['capital_used'] + pos['entry_fee'])
        pnl_pct = (pnl_rp / (pos['capital_used'] + pos['entry_fee'])) * 100
        pnl_r = pnl_rp / pos['risk_rupiah'] if pos['risk_rupiah'] > 0 else 0

        self.cash_balance += sell_value_net

        trades.append({
            "symbol": pos['symbol'],
            "strategy": pos['strategy'],
            "entry_ts": pos['entry_ts'],
            "exit_ts": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
            "entry_price": pos['entry_price'],
            "exit_price": exit_price_real,
            "qty": pos['qty'],
            "lots": pos['lots'],
            "capital_used": pos['capital_used'],
            "buy_fee": pos['entry_fee'],
            "sell_fee": sell_fee,
            "pnl": float(pnl_rp),
            "pnl_pct": float(pnl_pct),
            "r_multiple": float(pnl_r),
            "reason": reason,
            "balance_after": float(self.cash_balance),
            # FIX: hold_bars sebelumnya "Dummy" (ts.day - entry.day) yang rusak
            # kalau menyeberangi bulan. Dihitung dari selisih index bar,
            # yang sudah akurat dan tersedia dari pos['entry_idx'].
            "hold_bars": int(current_idx - pos['entry_idx'])
        })
        positions.remove(pos)

    @staticmethod
    def _compute_metrics_for(trades_list):
        """
        Hitung win_rate/expectancy/profit_factor/max_dd untuk satu kumpulan
        trade (dipakai baik untuk keseluruhan maupun per-strategi, §8c.6).
        """
        if not trades_list:
            return {
                "total_trades": 0, "win_rate": "0%", "expectancy": 0,
                "profit_factor": 0, "net_profit": 0,
                "sample_size_warning": True
            }
        df_t = pd.DataFrame(trades_list)
        wins = df_t[df_t['pnl'] > 0]
        losses = df_t[df_t['pnl'] <= 0]
        win_rate = len(wins) / len(trades_list) * 100
        avg_win_r = wins['r_multiple'].mean() if not wins.empty else 0
        avg_loss_r = abs(losses['r_multiple'].mean()) if not losses.empty else 0
        expectancy = (win_rate / 100 * avg_win_r) - ((1 - win_rate / 100) * avg_loss_r)
        total_profit = wins['pnl'].sum()
        total_loss = abs(losses['pnl'].sum())
        profit_factor = total_profit / total_loss if total_loss > 0 else (float('inf') if total_profit > 0 else 0)
        return {
            "total_trades": len(trades_list),
            "win_rate": f"{win_rate:.1f}%",
            "expectancy": round(float(expectancy), 3),
            "profit_factor": round(float(profit_factor), 2) if not np.isinf(profit_factor) else "∞",
            "net_profit": float(df_t['pnl'].sum()),
            # §8c.6: sample_size < 30 -> hasil TIDAK signifikan secara statistik
            "sample_size_warning": len(trades_list) < 30
        }

    def _summarize(self, trades, equity_curve, skip_stats, symbol, timeframe, df, indicators):
        # Prepare candles for frontend
        formatted_candles = []
        df_reset = df.reset_index()
        time_col = next((c for c in df_reset.columns if c.lower() in ['date', 'datetime', 'ts', 'index']), None)

        for i, row in df_reset.iterrows():
            ts_val = row[time_col]
            timestamp = int(ts_val.timestamp()) if hasattr(ts_val, 'timestamp') else int(ts_val)

            ao_val = indicators['AO'].iloc[i] if not indicators['AO'].empty else 0

            formatted_candles.append({
                "time": timestamp,
                "open": float(row['Open']),
                "high": float(row['High']),
                "low": float(row['Low']),
                "close": float(row['Close']),
                "volume": int(row['Volume']),
                "ao": float(ao_val) if not np.isnan(ao_val) else 0
            })

        base_skip_fields = {
            "unfilled_ara": skip_stats["unfilled_ara"],
            "skipped_capital": skip_stats["skipped_capital"],
            "skipped_risk_too_small": skip_stats["skipped_risk_too_small"],
            "skipped_invalid_setup": skip_stats["skipped_invalid_setup"],
            "blocked_arb_exits": skip_stats["blocked_arb_exits"],
        }

        if not trades:
            return {
                "metrics": {
                    "total_trades": 0,
                    "net_profit": 0,
                    "win_rate": "0%",
                    "expectancy": 0,
                    "profit_factor": 0,
                    "max_drawdown": "0%",
                    "sample_size_warning": True,
                    **base_skip_fields
                },
                "metrics_by_strategy": {},
                "trades": [],
                "equity_curve": equity_curve,
                "history_candles": formatted_candles,
                "symbol": symbol,
                "timeframe": timeframe,
                "cash_balance": self.cash_balance,
                "total_equity": self.cash_balance
            }

        # ============================================================
        # §8c.6: metrik WAJIB dipisah per strategi, karena karakteristik
        # risk/reward tiap metode berbeda (lihat tabel §8 dokumen CTG).
        # Menggabung semuanya jadi satu angka menyembunyikan strategi mana
        # yang sebenarnya sehat dan mana yang menyeret rata-rata ke bawah.
        # ============================================================
        overall_metrics = self._compute_metrics_for(trades)

        metrics_by_strategy = {}
        strategy_names = sorted(set(t['strategy'] for t in trades))
        for sname in strategy_names:
            sub_trades = [t for t in trades if t['strategy'] == sname]
            metrics_by_strategy[sname] = self._compute_metrics_for(sub_trades)

        # Drawdown calculation (dari equity curve keseluruhan, bukan per-strategi,
        # karena drawdown adalah properti portofolio gabungan)
        equity_vals = np.array([e['value'] for e in equity_curve], dtype=float)
        peak = np.maximum.accumulate(equity_vals)
        peak[peak == 0] = 1
        drawdown = (equity_vals / peak) - 1
        max_dd = drawdown.min() * 100 if len(drawdown) else 0.0

        results = {
            "metrics": {
                **overall_metrics,
                "max_drawdown": f"{max_dd:.1f}%",
                **base_skip_fields
            },
            "metrics_by_strategy": metrics_by_strategy,
            "trades": trades,
            "equity_curve": equity_curve,
            "history_candles": formatted_candles,
            "symbol": symbol,
            "timeframe": timeframe,
            "cash_balance": float(self.cash_balance),
            "total_equity": float(equity_vals[-1]) if len(equity_vals) else float(self.cash_balance),
            "engine_version": "V4.3.0-CTG-PRO-FIXED"
        }

        self._save_to_db(results, symbol, timeframe)
        return results

    def _save_to_db(self, results, symbol, timeframe):
        try:
            run_data = {
                "strategy": "Multi-Strategy Portfolio",
                "symbol": symbol,
                "timeframe": timeframe,
                "trade_count": results['metrics']['total_trades'],
                "win_rate": float(results['metrics']['win_rate'].replace('%', '')),
                "expectancy": results['metrics']['expectancy'],
                "profit_factor": results['metrics']['profit_factor'] if results['metrics']['profit_factor'] != "∞" else 999,
                "max_drawdown": float(results['metrics']['max_drawdown'].replace('%', '')),
                # §8c.6/§8c.7: sample < 30 -> belum signifikan secara statistik,
                # jangan divonis "PROVEN_POSITIVE" walau expectancy kebetulan > 0
                "verdict": (
                    "NOT_PROVEN_SMALL_SAMPLE" if results['metrics'].get('sample_size_warning')
                    else ("PROVEN_POSITIVE" if results['metrics']['expectancy'] > 0 else "NEGATIVE_EXPECTANCY")
                )
            }
            resp = supabase.table("backtest_runs").insert(run_data).execute()
            if resp.data:
                run_id = resp.data[0]['id']
                trades_data = []
                for t in results['trades']:
                    trades_data.append({
                        "run_id": run_id,
                        "symbol": symbol,
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