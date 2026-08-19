import math
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import pandas as pd
from app.core.database import supabase
from app.scanner.scanner_core import Fees, round_to_tick, is_idx_market_open

class VirtualBroker:
    def __init__(self, session_id: int):
        self.session_id = session_id
        self.fees = Fees()

    def get_session_info(self) -> Dict[str, Any]:
        res = supabase.table("backtest_sessions").select("*").eq("id", self.session_id).single().execute()
        return res.data if res.data else {}

    def get_portfolio(self) -> List[Dict[str, Any]]:
        res = supabase.table("backtest_positions").select("*").eq("session_id", self.session_id).execute()
        return res.data if res.data else []

    def sync_positions_with_market(self):
        """
        Scans all active positions and pending orders.
        1. Triggers Stop Loss / Take Profit for open positions.
        2. Executes PENDING orders if market is open.
        """
        market_open = is_idx_market_open()

        # --- A. Sync PENDING Orders ---
        if market_open:
            self.process_pending_orders()

        # --- B. Sync SL/TP for Open Positions ---
        positions = self.get_portfolio()
        if not positions: return

        for pos in positions:
            symbol = pos["symbol"]
            # Get latest price from stock_master
            stock_res = supabase.table("stock_master").select("last_price").eq("symbol", symbol).single().execute()
            if not stock_res.data or stock_res.data["last_price"] is None: continue

            last_price = float(stock_res.data["last_price"])

            # Check SL
            if pos["stop_loss"] and last_price <= float(pos["stop_loss"]):
                print(f"🚨 SL TRIGGERED for {symbol} at {last_price}")
                self._execute_trade(symbol, "SELL", pos["quantity"], last_price, source="STOP_LOSS")

            # Check TP
            elif pos["take_profit"] and last_price >= float(pos["take_profit"]):
                print(f"💰 TP TRIGGERED for {symbol} at {last_price}")
                self._execute_trade(symbol, "SELL", pos["quantity"], last_price, source="TAKE_PROFIT")

    def process_pending_orders(self):
        """Executes all orders with status PENDING for this session."""
        res = supabase.table("backtest_orders").select("*").eq("session_id", self.session_id).eq("status", "PENDING").execute()
        if not res.data: return

        for order in res.data:
            try:
                # Use current market price if available, else use order price
                stock_res = supabase.table("stock_master").select("last_price").eq("symbol", order["symbol"]).single().execute()
                price = float(stock_res.data["last_price"]) if stock_res.data and stock_res.data["last_price"] else float(order["price"])

                self._execute_trade(
                    order["symbol"], order["side"], order["quantity"], price,
                    stop_loss=order.get("stop_loss"), take_profit=order.get("take_profit"),
                    source=order.get("source", "MANUAL")
                )
                # Mark order as FILLED
                supabase.table("backtest_orders").update({"status": "FILLED", "filled_at": datetime.now(timezone.utc).isoformat()}).eq("id", order["id"]).execute()
            except Exception as e:
                print(f"⚠️ Failed to process pending order {order['id']}: {e}")

    def place_order(self, symbol: str, side: str, quantity: int, price: float,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None,
                    source: str = "MANUAL") -> Dict[str, Any]:
        """
        Public method to place an order.
        If market is open, executes immediately.
        If market is closed, saves as PENDING.
        """
        symbol = symbol.upper()
        if is_idx_market_open():
            return self._execute_trade(symbol, side, quantity, price, stop_loss, take_profit, source)
        else:
            # Queue order
            supabase.table("backtest_orders").insert({
                "session_id": self.session_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "status": "PENDING",
                "source": source
            }).execute()
            return {"status": "QUEUED", "message": "Market closed. Order queued for next opening."}

    def _execute_trade(self, symbol: str, side: str, quantity: int, price: float,
                    stop_loss: Optional[float] = None,
                    take_profit: Optional[float] = None,
                    source: str = "MANUAL") -> Dict[str, Any]:
        """Internal execution logic."""
        session = self.get_session_info()
        if not session:
            raise Exception("Session not found")

        current_balance = float(session["current_balance"])
        gross_amount = quantity * price
        fee = gross_amount * (self.fees.buy_pct if side == "BUY" else self.fees.sell_pct)
        net_amount = gross_amount + fee if side == "BUY" else gross_amount - fee

        if side == "BUY":
            if net_amount > current_balance:
                raise Exception(f"Insufficient balance. Required: Rp {net_amount:,.0f}, Available: Rp {current_balance:,.0f}")

            new_balance = current_balance - net_amount
            self._update_position_buy(symbol, quantity, price, stop_loss, take_profit)
            self._record_transaction(symbol, side, quantity, price, gross_amount, fee, net_amount, source=source)
            self._update_session_balance(new_balance)

        elif side == "SELL":
            pos_res = supabase.table("backtest_positions").select("*").eq("session_id", self.session_id).eq("symbol", symbol).execute()
            if not pos_res.data:
                raise Exception(f"No position found for {symbol}")

            pos = pos_res.data[0]
            if quantity > pos["quantity"]:
                raise Exception(f"Insufficient quantity. Requested: {quantity}, Owned: {pos['quantity']}")

            new_balance = current_balance + net_amount
            cost_basis_per_share = float(pos["avg_price"]) * (1 + self.fees.buy_pct)
            realized_pnl = (price * quantity - fee) - (cost_basis_per_share * quantity)
            realized_pnl_pct = (realized_pnl / (cost_basis_per_share * quantity)) * 100

            self._update_position_sell(symbol, quantity)
            self._record_transaction(symbol, side, quantity, price, gross_amount, fee, net_amount,
                                    realized_pnl=realized_pnl, realized_pnl_pct=realized_pnl_pct,
                                    source=source, exit_reason=source if source != "MANUAL" else "MANUAL")
            self._update_session_balance(new_balance)

        return {"status": "SUCCESS", "new_balance": new_balance}

    def _update_position_buy(self, symbol: str, quantity: int, price: float,
                             stop_loss: Optional[float], take_profit: Optional[float]):
        res = supabase.table("backtest_positions").select("*").eq("session_id", self.session_id).eq("symbol", symbol).execute()

        if res.data:
            pos = res.data[0]
            old_qty = int(pos["quantity"])
            old_avg = float(pos["avg_price"])
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty

            update_data = {
                "avg_price": new_avg, "quantity": new_qty,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            if stop_loss: update_data["stop_loss"] = stop_loss
            if take_profit: update_data["take_profit"] = take_profit
            supabase.table("backtest_positions").update(update_data).eq("id", pos["id"]).execute()
        else:
            supabase.table("backtest_positions").insert({
                "session_id": self.session_id, "symbol": symbol, "avg_price": price,
                "quantity": quantity, "stop_loss": stop_loss, "take_profit": take_profit
            }).execute()

    def _update_position_sell(self, symbol: str, quantity: int):
        res = supabase.table("backtest_positions").select("*").eq("session_id", self.session_id).eq("symbol", symbol).single().execute()
        if not res.data: return
        pos = res.data
        new_qty = int(pos["quantity"]) - quantity
        if new_qty <= 0:
            supabase.table("backtest_positions").delete().eq("id", pos["id"]).execute()
        else:
            supabase.table("backtest_positions").update({
                "quantity": new_qty, "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", pos["id"]).execute()

    def _update_session_balance(self, new_balance: float):
        supabase.table("backtest_sessions").update({
            "current_balance": new_balance, "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", self.session_id).execute()

    def _record_transaction(self, symbol: str, side: str, quantity: int, price: float,
                           gross: float, fee: float, net: float,
                           realized_pnl: float = 0, realized_pnl_pct: float = 0,
                           source: str = "MANUAL", exit_reason: Optional[str] = None):
        supabase.table("backtest_transactions").insert({
            "session_id": self.session_id, "symbol": symbol, "side": side,
            "quantity": quantity, "price": price, "gross_amount": gross, "fee": fee,
            "net_amount": net, "realized_pnl": realized_pnl, "realized_pnl_pct": realized_pnl_pct,
            "source": source, "exit_reason": exit_reason
        }).execute()

    def reset_session(self):
        session = self.get_session_info()
        if not session: return
        supabase.table("backtest_sessions").update({
            "current_balance": session["initial_balance"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", self.session_id).execute()
        supabase.table("backtest_positions").delete().eq("session_id", self.session_id).execute()
        supabase.table("backtest_transactions").delete().eq("session_id", self.session_id).execute()
        supabase.table("backtest_portfolio_snapshots").delete().eq("session_id", self.session_id).execute()

    @staticmethod
    def create_session(user_id: str, name: str, initial_balance: float = 1000000000000) -> Dict[str, Any]:
        res = supabase.table("backtest_sessions").insert({
            "user_id": user_id, "name": name, "initial_balance": initial_balance, "current_balance": initial_balance
        }).execute()
        return res.data[0] if res.data else {}
