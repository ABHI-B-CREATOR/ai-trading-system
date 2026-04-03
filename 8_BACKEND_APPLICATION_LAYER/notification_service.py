from datetime import datetime
from typing import Dict, List, Any


class NotificationService:
    """
    Handles real-time notifications for trading events, alerts, and system updates.
    """

    def __init__(self):
        self.notifications: List[Dict[str, Any]] = []
        self.subscribers: List[callable] = []
        print("📨 Notification Service Initialised")

    def subscribe(self, callback: callable) -> None:
        """Subscribe callback function for real-time notifications"""
        self.subscribers.append(callback)

    def broadcast(self, notification: Dict[str, Any]) -> None:
        """Broadcast notification to all subscribers"""
        notification["timestamp"] = datetime.utcnow().isoformat()
        self.notifications.append(notification)
        
        for subscriber in self.subscribers:
            try:
                subscriber(notification)
            except Exception as e:
                print(f"⚠️ Error in notification subscriber: {e}")

    def notify_trade(self, trade_id: str, symbol: str, side: str, quantity: float, price: float) -> None:
        """Notify when a trade is executed"""
        notification = {
            "type": "TRADE_EXECUTED",
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price
        }
        self.broadcast(notification)

    def notify_signal(self, strategy: str, symbol: str, action: str, confidence: float) -> None:
        """Notify when a strategy generates a signal"""
        notification = {
            "type": "STRATEGY_SIGNAL",
            "strategy": strategy,
            "symbol": symbol,
            "action": action,
            "confidence": confidence
        }
        self.broadcast(notification)

    def notify_risk_event(self, event_type: str, message: str, severity: str = "INFO") -> None:
        """Notify risk-related events"""
        notification = {
            "type": "RISK_EVENT",
            "event_type": event_type,
            "message": message,
            "severity": severity
        }
        self.broadcast(notification)

    def notify_system(self, event: str, details: Dict[str, Any] = None) -> None:
        """Notify system-level events"""
        notification = {
            "type": "SYSTEM_EVENT",
            "event": event,
            "details": details or {}
        }
        self.broadcast(notification)

    def get_recent_notifications(self, count: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent notifications"""
        return self.notifications[-count:]

    def clear_notifications(self) -> None:
        """Clear all stored notifications"""
        self.notifications.clear()

    def send_alert(self, level: str, title: str, message: str) -> None:
        """
        Send a system alert with severity level.
        Levels: info, warning, critical
        """
        notification = {
            "type": "SYSTEM_ALERT",
            "level": level.upper(),
            "title": title,
            "message": message,
            "requires_action": level.lower() == "critical"
        }
        self.broadcast(notification)
        
        # Print to console with appropriate formatting
        if level.lower() == "critical":
            print(f"🚨 CRITICAL: {title} - {message}")
        elif level.lower() == "warning":
            print(f"⚠️ WARNING: {title} - {message}")
        else:
            print(f"ℹ️ INFO: {title} - {message}")
        
        # Play sound for critical alerts (Windows)
        if level.lower() == "critical":
            try:
                import winsound
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass


class AuthManager:

    def __init__(self):

        # simple in-memory session store (later move to Redis / DB)
        self.sessions = {}

        # demo user store (later DB / encrypted vault)
        self.users = {
            "admin": self._hash("admin123"),
            "trader": self._hash("trade123")
        }

        print("🔐 Auth Manager Initialised")

    # -------------------------------------------------

    def _hash(self, text):
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()

    # -------------------------------------------------

    def login(self, username, password):

        stored = self.users.get(username)

        if not stored:
            return None

        if stored != self._hash(password):
            return None

        import uuid
        token = str(uuid.uuid4())

        self.sessions[token] = {
            "user": username,
            "expiry": datetime.utcnow() + __import__('datetime').timedelta(hours=8)
        }

        print(f"✅ User Logged In → {username}")

        return token

    # -------------------------------------------------

    def validate_token(self, token):

        session = self.sessions.get(token)

        if not session:
            return False

        if session["expiry"] < datetime.utcnow():
            del self.sessions[token]
            return False

        return True

    # -------------------------------------------------

    def logout(self, token):

        if token in self.sessions:
            del self.sessions[token]
            print("🚪 Session Logged Out")

    # -------------------------------------------------

    def get_user(self, token):

        session = self.sessions.get(token)

        if not session:
            return None

        return session["user"]