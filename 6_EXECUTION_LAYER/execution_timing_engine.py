import time
from datetime import datetime


class ExecutionTimingEngine:

    def __init__(self, config: dict):

        self.momentum_entry_threshold = config.get(
            "momentum_entry_threshold", 0.3
        )

        self.max_spread_allowed = config.get(
            "max_spread_allowed", 1.0
        )

        self.fake_breakout_wait_sec = config.get(
            "fake_breakout_wait_sec", 2
        )

        self.last_execution_time = None

    # ---------- SPREAD FILTER ----------
    def spread_ok(self, market_depth: dict):

        spread = market_depth.get("spread", 0)

        if spread > self.max_spread_allowed:
            return False

        return True

    # ---------- MOMENTUM BURST ----------
    def momentum_ready(self, micro_features: dict):

        velocity = micro_features.get("price_velocity", 0)

        if abs(velocity) >= self.momentum_entry_threshold:
            return True

        return False

    # ---------- BREAKOUT VALIDATION ----------
    def confirm_breakout(self, micro_features: dict):

        breakout_flag = micro_features.get("breakout_detected", False)

        if breakout_flag:
            time.sleep(self.fake_breakout_wait_sec)
            return True

        return True

    # ---------- MASTER TIMING DECISION ----------
    def allow_execution(self,
                        market_depth: dict,
                        micro_features: dict):

        if not self.spread_ok(market_depth):
            return False

        if not self.momentum_ready(micro_features):
            return False

        if not self.confirm_breakout(micro_features):
            return False

        self.last_execution_time = datetime.now()

        return True

    # ---------- STATUS ----------
    def timing_status(self):

        return {
            "last_execution_time": self.last_execution_time
        }