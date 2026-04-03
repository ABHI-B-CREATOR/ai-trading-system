import json
import os
from datetime import datetime


class TradeLogger:

    def __init__(self, config: dict = None):

        config = config or {}
        self.log_dir = config.get("trade_log_dir", "logs")
        self.file_name = config.get("trade_log_file", "trades.jsonl")

        os.makedirs(self.log_dir, exist_ok=True)

        self.file_path = os.path.join(self.log_dir, self.file_name)
        
        # ===== RUNTIME MEMORY =====
        self.trades = []

    # ---------- BUILD TRADE RECORD ----------
    def build_trade_record(self,
                           signal: dict,
                           order_id: str,
                           fill_price: float,
                           qty: int,
                           slippage: float,
                           status: str):

        record = {
            "timestamp": datetime.now().isoformat(),
            "order_id": order_id,
            "symbol": signal.get("symbol"),
            "direction": signal.get("direction"),
            "strategy": signal.get("strategy_source",
                                   signal.get("strategy")),
            "entry_price_signal": signal.get("entry_price"),
            "fill_price": fill_price,
            "quantity": qty,
            "slippage": slippage,
            "status": status
        }

        return record

    # ---------- WRITE LOG ----------
    def log_trade(self, record: dict):
        """Log trade to file and runtime memory"""
        
        # Store in runtime memory
        self.trades.append(record)

        # Write to file
        try:
            with open(self.file_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"⚠ Trade log write error: {e}")

    # ---------- RETRIEVE TRADES ----------
    def get_recent_trades(self, n: int = 50):
        """Get last N trades from runtime memory"""
        return self.trades[-n:]

    def get_all_trades(self):
        """Get all trades from runtime memory"""
        return self.trades

    # ---------- QUICK HELPER ----------
    def log_execution(self,
                      signal: dict,
                      order_id: str,
                      fill_price: float,
                      qty: int,
                      slippage: float,
                      status: str):

        record = self.build_trade_record(
            signal,
            order_id,
            fill_price,
            qty,
            slippage,
            status
        )

        self.log_trade(record)

        return record