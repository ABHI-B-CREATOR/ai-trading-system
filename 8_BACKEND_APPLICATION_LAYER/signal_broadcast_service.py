from datetime import datetime


class SignalBroadcastService:

    def __init__(self, websocket_engine=None):

        self.websocket_engine = websocket_engine
        self.execution_engine = None  # ===== EXECUTION ENGINE INJECTION =====
        self.risk_engine = None  # ===== RISK ENGINE INJECTION =====

        self.last_signal = None
        self.last_trade = None
        self.last_risk_event = None

        print("📡 Signal Broadcast Service Initialised")

    # -------------------------------------------------

    def broadcast_strategy_signal(self, strategy_name, signal_data):

        payload = {
            "event": "strategy_signal",
            "strategy": strategy_name,
            "data": signal_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.last_signal = payload

        if self.websocket_engine:
            self.websocket_engine.update_signal(payload)

        # ===== APPLY RISK CONTROLS =====
        signal = signal_data
        if self.risk_engine:
            signal = self.risk_engine.process_signal(signal_data)

        # ===== EXECUTE APPROVED ORDER =====
        if signal and self.execution_engine:
            self.execution_engine.execute_order(signal)

        print(f"⚡ Signal Broadcasted → {strategy_name}")

    # -------------------------------------------------

    def broadcast_trade_execution(self, trade_data):

        payload = {
            "event": "trade_execution",
            "data": trade_data,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.last_trade = payload

        if self.websocket_engine:
            self.websocket_engine.update_pnl(trade_data)

        print("💰 Trade Execution Broadcasted")

    # -------------------------------------------------

    def broadcast_risk_event(self, risk_msg):

        payload = {
            "event": "risk_alert",
            "message": risk_msg,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.last_risk_event = payload

        if self.websocket_engine:
            self.websocket_engine.update_system_status(payload)

        print("🛑 Risk Event Broadcasted")

    # -------------------------------------------------

    def attach_websocket(self, websocket_engine):

        self.websocket_engine = websocket_engine
        print("🔗 WebSocket Engine Attached To Broadcast Service")

    # -------------------------------------------------

    def attach_execution_engine(self, execution_engine):
        """Attach order router for automatic execution"""
        self.execution_engine = execution_engine
        print("🔗 Execution Engine Attached To Broadcast Service")

    # -------------------------------------------------

    def attach_risk_engine(self, risk_engine):
        """Attach risk engine for signal processing"""
        self.risk_engine = risk_engine
        print("🔗 Risk Engine Attached To Broadcast Service")