from datetime import datetime


class DrawdownController:

    def __init__(self, config: dict):

        self.max_allowed_drawdown = config.get("max_drawdown_pct", 15)
        self.soft_drawdown_level = config.get("soft_drawdown_pct", 7)

        self.equity_peak = None
        self.current_drawdown = 0
        self.risk_mode = "NORMAL"
        self.last_update = None

    # ---------- UPDATE EQUITY ----------
    def update_equity(self, current_equity: float):

        if self.equity_peak is None:
            self.equity_peak = current_equity

        if current_equity > self.equity_peak:
            self.equity_peak = current_equity

        dd = (self.equity_peak - current_equity) / self.equity_peak * 100
        self.current_drawdown = dd

        self._evaluate_risk_mode()

        self.last_update = datetime.now()

    # ---------- RISK MODE LOGIC ----------
    def _evaluate_risk_mode(self):

        if self.current_drawdown >= self.max_allowed_drawdown:
            self.risk_mode = "HARD_STOP"

        elif self.current_drawdown >= self.soft_drawdown_level:
            self.risk_mode = "DEFENSIVE"

        else:
            self.risk_mode = "NORMAL"

    # ---------- TRADE PERMISSION ----------
    def allow_new_trade(self):

        if self.risk_mode == "HARD_STOP":
            return False

        return True

    # ---------- POSITION SIZE MODIFIER ----------
    def risk_adjustment_factor(self):

        if self.risk_mode == "DEFENSIVE":
            return 0.5

        elif self.risk_mode == "HARD_STOP":
            return 0.0

        return 1.0

    # ---------- STATUS ----------
    def status(self):

        return {
            "equity_peak": self.equity_peak,
            "current_drawdown_pct": self.current_drawdown,
            "risk_mode": self.risk_mode,
            "last_update": self.last_update
        }