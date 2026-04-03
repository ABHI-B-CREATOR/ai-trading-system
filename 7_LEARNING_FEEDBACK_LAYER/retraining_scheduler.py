from datetime import datetime, timedelta


class RetrainingScheduler:

    def __init__(self, config: dict):

        self.trade_trigger = config.get("retrain_after_trades", 50)
        self.time_trigger_hours = config.get("retrain_after_hours", 24)
        self.market_close_hour = config.get("market_close_hour", 15)

        self.last_retrain_time = None
        self.trade_counter = 0

    # ---------- TRADE EVENT ----------
    def on_trade_recorded(self):

        self.trade_counter += 1

    # ---------- TIME CHECK ----------
    def time_due(self):

        if self.last_retrain_time is None:
            return False

        elapsed = datetime.now() - self.last_retrain_time

        return elapsed >= timedelta(hours=self.time_trigger_hours)

    # ---------- TRADE COUNT CHECK ----------
    def trade_due(self):

        return self.trade_counter >= self.trade_trigger

    # ---------- MARKET HOURS SAFETY ----------
    def safe_to_retrain(self):

        now = datetime.now()

        # avoid retraining during active market
        if now.hour < self.market_close_hour:
            return False

        return True

    # ---------- MASTER DECISION ----------
    def should_retrain(self):

        if not self.safe_to_retrain():
            return False

        if self.trade_due() or self.time_due():
            return True

        return False

    # ---------- RESET AFTER TRAIN ----------
    def mark_retrained(self):

        self.last_retrain_time = datetime.now()
        self.trade_counter = 0

    # ---------- STATUS ----------
    def scheduler_status(self):

        return {
            "last_retrain_time": self.last_retrain_time,
            "trade_counter": self.trade_counter
        }