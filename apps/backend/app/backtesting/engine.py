"""
Backtest Engine V4 -- implementasi final.md §8c.

Prinsip inti (§8c, tidak bisa ditawar): tugas backtest adalah MENGUKUR, bukan
MENGHASILKAN angka tertentu. Lima cacat yang wajib dicegah (§8c tabel):
lookahead bias, survivorship bias, overfitting parameter, cherry-picking
periode, dan biaya transaksi diabaikan.

Engine ini secara eksplisit menegakkan:
- Anti-lookahead (§8c.2): setiap keputusan entry HANYA memakai
  `window_df = df.iloc[:i+1]` (data s.d. candle yang SUDAH close), lalu
  entry dieksekusi di OPEN candle berikutnya (`next_bar['Open']`), bukan di
  close candle konfirmasi itu sendiri.
- ARA/ARB realistis (app/utils/market.py): entry tidak bisa terjadi di
  harga ARA (tidak ada seller), exit tidak bisa terjadi di harga ARB
  (tidak ada buyer) -- posisi yang harusnya exit tapi kena ARB akan
  ditunda ke bar berikutnya dan DICATAT (`blocked_arb_exits`), bukan
  didiamkan begitu saja.
- Biaya transaksi & slippage (§8c.4): lihat app/utils/market.py Fees &
  apply_fees_and_slippage -- slippage SELALU merugikan (asumsi konservatif).
- Metrik dipisah per strategi (§8c.6) karena karakteristik risk/reward tiap
  metode berbeda (§8, tabel perbandingan) -- digabung rata akan menyembunyikan
  strategi mana yang sehat dan mana yang menyeret rata-rata ke bawah.
- Sample size warning (§8c.6/§8c.7): total_trades < 30 per kelompok ditandai
  eksplisit sebagai TIDAK signifikan secara statistik.

CATATAN soal walk-forward (§8c.5): validasi anti-overfitting (split in-sample
/ out-of-sample / holdout) adalah tanggung jawab CALLER -- panggil `.run()`
tiga kali dengan potongan `df` yang berbeda sesuai periode, JANGAN mengubah
parameter/level Fibonacci antar potongan hanya supaya hasilnya cocok data
(§8c.5: "level Fib TETAP sesuai yang diajarkan, TIDAK boleh diubah-ubah cuma
supaya cocok data").
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

from app.scanner.scanner_core import PivotDetector
from app.scanner.scanner_core import MovementClassifier
from app.indicators.ta import calculate_rsi, calculate_macd, calculate_ao
from app.strategies.technical_logic import (
    BullishDivergenceStrategy,
    DoubleBullishDivergenceStrategy,
    CorrectionStrategy,
    HiddenBullishDivergenceStrategy
)
from app.core.market_utils import is_ara, is_arb, Fees
from app.core.database import supabase

# Jumlah bar minimum untuk indikator/pivot "pemanasan" sebelum mulai mencari
# setup -- supaya ATR(14)/RSI(14)/MACD(26)/AO(34) semua sudah punya data
# yang cukup dan tidak menghasilkan sinyal palsu dari NaN/data parsial.
WARMUP_BARS = 40

# Maksimal bar menahan posisi sebelum dipaksa keluar di TIMEOUT (dipakai
# simulate_forward-style exit di dalam loop utama). 20 bar dipilih sebagai
# default netral untuk swing setup -- sesuaikan per timeframe kalau perlu.
MAX_HOLD_BARS = 20


class BacktestEngineV4:
    def __init__(self, initial_balance: float = 100_000_000, risk_per_trade_pct: float = 1.0):
        self.initial_balance = initial_balance
        self.cash_balance = initial_balance
        self.risk_per_trade_pct = risk_per_trade_pct
        self.fees = Fees()

        self.pivot_detector = PivotDetector()
        self.movement_classifier = MovementClassifier()

        # Urutan strategi PENTING: Double Bullish Divergence dicek lebih
        # dulu supaya kalau memang ada pola double, itu yang dipakai
        # (bukan salah dianggap bullish-div biasa yang baru terbentuk).
        self.strategies = [
            DoubleBullishDivergenceStrategy(),
            BullishDivergenceStrategy(),
            CorrectionStrategy(),
            HiddenBullishDivergenceStrategy(),
        ]

    def run(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict[str, Any]:
        if df.empty or len(df) < WARMUP_BARS + 10:
            return {"error": "Insufficient data"}

        df = df[~df.index.duplicated(keep="last")].sort_index()

        macd_df = calculate_macd(df)
        all_indicators = {
            "RSI": calculate_rsi(df),
            "MACD": macd_df["macd"] if not macd_df.empty else pd.Series(index=df.index, dtype="float64"),
            "AO": calculate_ao(df),
        }

        trades = []
        equity_curve = []
        positions = []
        skip_stats = {
            "unfilled_ara": 0,
            "skipped_capital": 0,
            "skipped_risk_too_small": 0,
            "skipped_invalid_setup": 0,
            "blocked_arb_exits": 0,
        }

        for i in range(WARMUP_BARS, len(df) - 1):
            current_bar = df.iloc[i]
            next_bar = df.iloc[i + 1]
            ts = df.index[i]
            next_ts = df.index[i + 1]

            # 1. Cek EXIT untuk posisi terbuka. Urutan cek: SL dulu, baru TP
            #    (asumsi konservatif §8c.3: kalau SL & TP sama-sama kena di
            #    satu bar yang sama, SL dianggap menang duluan).
            for pos in positions[:]:
                exit_price, reason = None, None

                if current_bar["Low"] <= pos["sl"]:
                    exit_price = min(current_bar["Open"], pos["sl"])
                    reason = "STOP LOSS"
                elif current_bar["High"] >= pos["tp"]:
                    exit_price = max(current_bar["Open"], pos["tp"])
                    reason = "TAKE PROFIT"
                elif i - pos["entry_idx"] >= MAX_HOLD_BARS:
                    exit_price = current_bar["Close"]
                    reason = "TIMEOUT"

                if exit_price is not None:
                    prev_close = df.iloc[i - 1]["Close"]
                    if is_arb(exit_price, prev_close):
                        # Tidak ada buyer di harga ARB -- exit ditunda ke bar
                        # berikutnya, DICATAT (bukan diam-diam diabaikan).
                        skip_stats["blocked_arb_exits"] += 1
                        continue
                    self._execute_exit(pos, exit_price, reason, ts, i, trades, positions)

            # 2. Cek ENTRY (hanya kalau tidak sedang ada posisi terbuka --
            #    §3.7: dilarang all-in / menumpuk banyak setup sekaligus).
            if not positions:
                window_df = df.iloc[: i + 1].copy()
                window_df.attrs["symbol"] = symbol
                window_df.attrs["timeframe"] = timeframe

                # ANTI-LOOKAHEAD FOR PREDICTION (§1):
                # Gunakan data HANYA sampai bar i untuk memprediksi bar i+1.
                window_df = df.iloc[: i + 1].copy()
                window_df.attrs["symbol"] = symbol
                window_df.attrs["timeframe"] = timeframe

                # Sesuai logika Prediksi: deteksi pola pada data yang sudah ada
                # untuk memprediksi arah candle yang sedang berjalan/berikutnya.
                pivots = self.pivot_detector.detect_pivots(window_df)

                if not pivots.empty:
                    pivots = self.movement_classifier.classify_movements(pivots)
                    pivots = self.movement_classifier.label_5_movements(pivots)
                    pivots = self.movement_classifier.label_abcde(pivots)

                    curr_inds = {k: v.iloc[: i + 1] for k, v in all_indicators.items()}

                    for strategy in self.strategies:
                        setup = strategy.evaluate(window_df, pivots, curr_inds)
                        if setup is None or setup.status != "READY":
                            continue

                        entry_price_raw = float(next_bar["Open"])
                        prev_close = float(current_bar["Close"])

                        if is_ara(entry_price_raw, prev_close):
                            # Tidak ada seller di harga ARA -- order beli
                            # tidak bisa terisi, setup ini dilewati.
                            skip_stats["unfilled_ara"] += 1
                            break

                        result = self._execute_entry(setup, entry_price_raw, next_ts, i + 1, positions)
                        if result == "invalid_setup":
                            skip_stats["skipped_invalid_setup"] += 1
                        elif result == "risk_too_small":
                            skip_stats["skipped_risk_too_small"] += 1
                        elif result in ("insufficient_capital", False):
                            skip_stats["skipped_capital"] += 1
                        break  # satu setup per bar sudah cukup

            # 3. Catat equity
            open_pos_val = sum(p["qty"] * current_bar["Close"] for p in positions)
            equity_curve.append({"time": int(ts.timestamp()), "value": float(self.cash_balance + open_pos_val)})

        return self._summarize(trades, equity_curve, skip_stats, symbol, timeframe, df, all_indicators)

    def _execute_entry(self, setup, price_raw, ts, idx, positions):
        # Validasi struktural WAJIB (§3.4/§3.5/§4.3/§4.4/§5.3/§5.4): untuk
        # setup long-only, urutan harga HARUS SL < entry < TP. Kalau modul
        # strategi menghasilkan level yang keliru, engine menolak di sini --
        # bukan membiarkan trade aneh lolos lalu keluar berlabel TAKE PROFIT
        # padahal sebenarnya rugi.
        if setup.stop_loss is None or setup.take_profit is None:
            return "invalid_setup"
        if not (setup.stop_loss < price_raw < setup.take_profit):
            return "invalid_setup"

        risk_rupiah = self.cash_balance * (self.risk_per_trade_pct / 100)
        jarak_sl = abs(price_raw - setup.stop_loss)
        if jarak_sl == 0:
            return "invalid_setup"

        lembar_ideal = risk_rupiah / jarak_sl
        jumlah_lot = int(np.floor(lembar_ideal / 100))

        if jumlah_lot <= 0:
            # Risiko per lot sudah melebihi anggaran risk_rupiah -- ini soal
            # UKURAN RISIKO, bukan kekurangan modal, jadi dilaporkan terpisah
            # dari skipped_capital.
            return "risk_too_small"

        total_buy_cost_raw = jumlah_lot * 100 * price_raw
        buy_fee = total_buy_cost_raw * self.fees.buy_pct
        total_required = total_buy_cost_raw + buy_fee

        if total_required > self.cash_balance:
            jumlah_lot = int(np.floor(self.cash_balance / (price_raw * 100 * (1 + self.fees.buy_pct))))
            if jumlah_lot <= 0:
                return "insufficient_capital"
            total_buy_cost_raw = jumlah_lot * 100 * price_raw
            buy_fee = total_buy_cost_raw * self.fees.buy_pct
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
            "entry_ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "entry_idx": idx,
            "risk_rupiah": risk_rupiah,
            "capital_used": total_buy_cost_raw,
        })
        return "ok"

    def _execute_exit(self, pos, price_raw, reason, ts, current_idx, trades, positions):
        # Slippage & fee sesuai §8c.4 -- slippage SELALU merugikan (harga
        # eksekusi riil lebih buruk dari harga ideal candle).
        exit_price_real = price_raw * (1 - self.fees.slippage_pct)
        sell_value_raw = exit_price_real * pos["qty"]
        sell_fee = sell_value_raw * self.fees.total_sell_pct  # sudah termasuk PPh final 0.1%
        sell_value_net = sell_value_raw - sell_fee

        pnl_rp = sell_value_net - (pos["capital_used"] + pos["entry_fee"])
        pnl_pct = (pnl_rp / (pos["capital_used"] + pos["entry_fee"])) * 100
        pnl_r = pnl_rp / pos["risk_rupiah"] if pos["risk_rupiah"] > 0 else 0

        self.cash_balance += sell_value_net

        trades.append({
            "symbol": pos["symbol"],
            "strategy": pos["strategy"],
            "entry_ts": pos["entry_ts"],
            "exit_ts": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "entry_price": pos["entry_price"],
            "exit_price": exit_price_real,
            "qty": pos["qty"],
            "lots": pos["lots"],
            "capital_used": pos["capital_used"],
            "buy_fee": pos["entry_fee"],
            "sell_fee": sell_fee,
            "pnl": float(pnl_rp),
            "pnl_pct": float(pnl_pct),
            "r_multiple": float(pnl_r),
            "reason": reason,
            "balance_after": float(self.cash_balance),
            "hold_bars": int(current_idx - pos["entry_idx"]),
        })
        positions.remove(pos)

    @staticmethod
    def _compute_metrics_for(trades_list) -> Dict[str, Any]:
        """Metrik §8c.6, dihitung baik untuk keseluruhan maupun per-strategi."""
        if not trades_list:
            return {
                "total_trades": 0, "win_rate": "0%", "expectancy": 0,
                "profit_factor": 0, "net_profit": 0, "sample_size_warning": True,
            }
        df_t = pd.DataFrame(trades_list)
        wins = df_t[df_t["pnl"] > 0]
        losses = df_t[df_t["pnl"] <= 0]

        win_rate = len(wins) / len(trades_list) * 100
        avg_win_r = wins["r_multiple"].mean() if not wins.empty else 0.0
        avg_loss_r = abs(losses["r_multiple"].mean()) if not losses.empty else 0.0
        expectancy = (win_rate / 100 * avg_win_r) - ((1 - win_rate / 100) * avg_loss_r)

        total_profit = wins["pnl"].sum()
        total_loss = abs(losses["pnl"].sum())
        profit_factor = (total_profit / total_loss) if total_loss > 0 else (float("inf") if total_profit > 0 else 0.0)

        return {
            "total_trades": len(trades_list),
            "win_rate": f"{win_rate:.1f}%",
            "expectancy": round(float(expectancy), 3),
            "profit_factor": round(float(profit_factor), 2) if not np.isinf(profit_factor) else "∞",
            "net_profit": float(df_t["pnl"].sum()),
            # §8c.6: sample < 30 -> hasil TIDAK signifikan secara statistik.
            "sample_size_warning": len(trades_list) < 30,
        }

    def _summarize(self, trades, equity_curve, skip_stats, symbol, timeframe, df, indicators):
        formatted_candles = []
        df_reset = df.reset_index()
        time_col = next((c for c in df_reset.columns if c.lower() in ["date", "datetime", "ts", "index"]), None)

        for i, row in df_reset.iterrows():
            ts_val = row[time_col]
            timestamp = int(ts_val.timestamp()) if hasattr(ts_val, "timestamp") else int(ts_val)
            ao_val = indicators["AO"].iloc[i] if not indicators["AO"].empty else 0.0
            formatted_candles.append({
                "time": timestamp,
                "open": float(row["Open"]), "high": float(row["High"]),
                "low": float(row["Low"]), "close": float(row["Close"]),
                "volume": int(row["Volume"]),
                "ao": float(ao_val) if not np.isnan(ao_val) else 0.0,
            })

        if not trades:
            return {
                "metrics": {
                    "total_trades": 0, "net_profit": 0, "win_rate": "0%",
                    "expectancy": 0, "profit_factor": 0, "max_drawdown": "0%",
                    "sample_size_warning": True, **skip_stats,
                },
                "metrics_by_strategy": {},
                "trades": [], "equity_curve": equity_curve,
                "history_candles": formatted_candles,
                "symbol": symbol, "timeframe": timeframe,
                "cash_balance": self.cash_balance, "total_equity": self.cash_balance,
            }

        # §8c.6: metrik WAJIB dipisah per strategi -- karakteristik risk/reward
        # tiap metode berbeda (lihat tabel §8), menggabung jadi satu angka
        # menyembunyikan mana yang sehat dan mana yang menyeret rata-rata turun.
        overall_metrics = self._compute_metrics_for(trades)
        metrics_by_strategy = {
            sname: self._compute_metrics_for([t for t in trades if t["strategy"] == sname])
            for sname in sorted(set(t["strategy"] for t in trades))
        }

        equity_vals = np.array([e["value"] for e in equity_curve], dtype=float)
        peak = np.maximum.accumulate(equity_vals)
        peak[peak == 0] = 1
        drawdown = (equity_vals / peak) - 1
        max_dd = drawdown.min() * 100 if len(drawdown) else 0.0

        results = {
            "metrics": {**overall_metrics, "max_drawdown": f"{max_dd:.1f}%", **skip_stats},
            "metrics_by_strategy": metrics_by_strategy,
            "trades": trades,
            "equity_curve": equity_curve,
            "history_candles": formatted_candles,
            "symbol": symbol, "timeframe": timeframe,
            "cash_balance": float(self.cash_balance),
            "total_equity": float(equity_vals[-1]) if len(equity_vals) else float(self.cash_balance),
            "engine_version": "V4.4.0-CTG-COMPLETE",
        }

        self._save_to_db(results, symbol, timeframe)
        return results

    def _save_to_db(self, results, symbol, timeframe):
        """Penyimpanan OPSIONAL ke Supabase -- lihat app/core/database.py.
        Kalau `supabase` None (tidak dikonfigurasi), fungsi ini tidak melakukan apa-apa."""
        if supabase is None:
            return
        try:
            run_data = {
                "strategy": "Multi-Strategy Portfolio",
                "symbol": symbol,
                "timeframe": timeframe,
                "trade_count": results["metrics"]["total_trades"],
                "win_rate": float(results["metrics"]["win_rate"].replace("%", "")),
                "expectancy": results["metrics"]["expectancy"],
                "profit_factor": (results["metrics"]["profit_factor"]
                                   if results["metrics"]["profit_factor"] != "∞" else 999),
                "max_drawdown": float(results["metrics"]["max_drawdown"].replace("%", "")),
                # §8c.6/§8c.7: sample < 30 -> belum signifikan secara statistik,
                # jangan divonis "PROVEN_POSITIVE" walau expectancy kebetulan > 0.
                "verdict": (
                    "NOT_PROVEN_SMALL_SAMPLE" if results["metrics"].get("sample_size_warning")
                    else ("PROVEN_POSITIVE" if results["metrics"]["expectancy"] > 0 else "NEGATIVE_EXPECTANCY")
                ),
            }
            resp = supabase.table("backtest_runs").insert(run_data).execute()
            if resp.data:
                run_id = resp.data[0]["id"]
                trades_data = [{
                    "run_id": run_id, "symbol": symbol, "strategy": t["strategy"],
                    "entry_date": t["entry_ts"], "exit_date": t["exit_ts"],
                    "entry_price": t["entry_price"], "exit_price": t["exit_price"],
                    "net_pnl": t["pnl"], "r_multiple": t["r_multiple"], "exit_reason": t["reason"],
                } for t in results["trades"]]
                if trades_data:
                    supabase.table("backtest_trades").insert(trades_data).execute()
        except Exception as e:
            print(f"Error saving backtest to DB: {e}")
