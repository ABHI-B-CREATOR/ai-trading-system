import json
import sys
import os
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '5_RISK_PORTFOLIO_LAYER'))

try:
    from sebi_ip_compliance import get_ip_compliance  # type: ignore
except ImportError:
    get_ip_compliance = None


class OrderRouter:

    def __init__(self, broker_session_path="6_EXECUTION_LAYER/broker_auth_session.json",
                 trade_logger=None,
                 broadcast_service=None,
                 notification_service=None):
        """
        Unified order router supporting both paper and live trading.

        broker_session_path: Path to broker auth JSON
        trade_logger: Trade logging service
        broadcast_service: Signal broadcast pipeline
        notification_service: Alert/notification engine
        """
        self.trade_logger = trade_logger
        self.broadcast_service = broadcast_service
        self.notification_service = notification_service

        try:
            with open(broker_session_path) as f:
                self.broker_session = json.load(f)
        except Exception as e:
            print(f"Warning: broker session load failed: {e}")
            self.broker_session = {}

        self.active_orders = {}
        self.paper_trading_mode = bool(self.broker_session.get("paper_trading_mode", True))
        self.max_market_spread = float(self.broker_session.get("max_market_spread", 0.5))

        # These integrations are optional in the current app wiring.
        self.broker_api = None
        self.risk_checks = None
        
        # SEBI IP Compliance checker
        self.ip_compliance = get_ip_compliance() if get_ip_compliance else None

        print("Order Router Initialised")

    # -------------------------------------------------

    def execute_order(self, signal: dict, qty: int | None = None, market_depth: dict | None = None):
        """
        Execute a strategy signal.

        The current app calls this with only `signal` for paper trading.
        A future live-trading path can also pass `qty` and `market_depth`.
        """
        # SEBI IP Compliance Check (for live orders)
        if not self.paper_trading_mode and self.ip_compliance:
            ip_check = self.ip_compliance.validate_order_ip()
            if not ip_check.get("allowed", True):
                error_msg = f"ORDER BLOCKED: {ip_check.get('reason', 'IP compliance check failed')}"
                print(f"🚨 {error_msg}")
                if self.notification_service:
                    self.notification_service.send_alert(
                        level="critical",
                        title="Order Blocked - SEBI IP",
                        message=error_msg
                    )
                return {
                    "status": "REJECTED",
                    "reason": error_msg,
                    "ip_compliance": ip_check
                }
        
        resolved_qty = qty if qty is not None else signal.get("qty", 1)

        if (
            not self.paper_trading_mode
            and market_depth is not None
            and self.broker_api is not None
        ):
            return self._execute_broker_order(signal, resolved_qty, market_depth)

        return self._execute_paper_order(signal, resolved_qty)

    # -------------------------------------------------

    def _execute_paper_order(self, signal: dict, qty: int):
        try:
            symbol = signal.get("symbol", "UNKNOWN")
            side = signal.get("direction") or signal.get("side", "BUY")
            strategy = signal.get("strategy", "unknown")
            timestamp = signal.get("timestamp", datetime.now().isoformat())

            order_id = f"SIM-{abs(hash(f'{symbol}:{side}:{timestamp}')):08d}"[:12]

            trade = {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "entry_price": signal.get("entry_price"),
                "stoploss": signal.get("stoploss"),
                "target": signal.get("target"),
                "strategy": strategy,
                "timestamp": timestamp,
                "status": "EXECUTED"
            }

            if self.trade_logger:
                self.trade_logger.log_trade(trade)

            if self.broadcast_service:
                self.broadcast_service.broadcast_trade_execution(trade)

            if self.notification_service:
                self.notification_service.notify_trade(trade)

            print(f"Order Executed -> {symbol} {side} qty={qty}")
            return trade

        except Exception as e:
            print(f"Order Execution Error -> {e}")
            return None

    # -------------------------------------------------

    def decide_order_type(self, signal: dict, market_depth: dict):
        spread = market_depth.get("spread", 0)
        if spread <= self.max_market_spread:
            return "MARKET"

        return "LIMIT"

    def compute_limit_price(self, signal: dict, market_depth: dict):
        best_bid = market_depth.get("best_bid")
        best_ask = market_depth.get("best_ask")
        direction = signal.get("direction") or signal.get("side")

        if direction == "BUY":
            return best_ask

        if direction == "SELL":
            return best_bid

        return signal.get("entry_price")

    def _execute_broker_order(self, signal: dict, qty: int, market_depth: dict):
        if self.risk_checks and not self.risk_checks.allow_trade(signal):
            return None

        order_type = self.decide_order_type(signal, market_depth)
        if order_type == "MARKET":
            price = signal.get("entry_price")
        else:
            price = self.compute_limit_price(signal, market_depth)

        order_payload = {
            "symbol": signal.get("symbol"),
            "side": signal.get("direction") or signal.get("side"),
            "qty": qty,
            "price": price,
            "order_type": order_type
        }

        order_id = self.broker_api.place_order(order_payload)

        self.active_orders[order_id] = {
            "payload": order_payload,
            "timestamp": datetime.now(),
            "status": "SENT"
        }

        return order_id

    # -------------------------------------------------

    def refresh_order_status(self):
        if not self.broker_api:
            return

        for oid in list(self.active_orders.keys()):
            status = self.broker_api.order_status(oid)
            self.active_orders[oid]["status"] = status

            if status in ["FILLED", "REJECTED", "CANCELLED"]:
                self.active_orders.pop(oid)

    def retry_unfilled(self):
        if not self.broker_api:
            return

        retry_window = int(self.broker_session.get("retry_seconds", 5))

        for oid, data in list(self.active_orders.items()):
            elapsed = (datetime.now() - data["timestamp"]).seconds
            if elapsed <= retry_window:
                continue

            self.broker_api.cancel_order(oid)

            payload = data["payload"]
            new_id = self.broker_api.place_order(payload)

            self.active_orders[new_id] = {
                "payload": payload,
                "timestamp": datetime.now(),
                "status": "RESENT"
            }

            self.active_orders.pop(oid)
