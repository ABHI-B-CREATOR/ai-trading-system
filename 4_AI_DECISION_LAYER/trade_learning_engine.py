from datetime import datetime


class TradeLearningEngine:

    def __init__(self, reinforcement_agent, performance_tracker):
        """
        reinforcement_agent → RL core
        performance_tracker → analytics module (later layer)
        """

        self.rl_agent = reinforcement_agent
        self.performance_tracker = performance_tracker

        self.last_update_time = None

    # ---------- MARKET STATE BUILDER ----------
    def build_market_state(self, trade_record: dict):

        state_features = {
            "regime": trade_record.get("market_regime"),
            "vol_bucket": trade_record.get("volatility_bucket"),
            "trend_strength_bucket": trade_record.get("trend_bucket"),
            "liquidity_bucket": trade_record.get("liquidity_bucket")
        }

        return self.rl_agent.build_state(state_features)

    # ---------- LEARNING PIPELINE ----------
    def process_trade_result(self, trade_record: dict):

        """
        trade_record example:
        {
            "strategy": str,
            "action": "BUY"/"SELL"/"SELL_PREMIUM",
            "pnl": float,
            "drawdown": float,
            "holding_time": int,
            "market_regime": str,
            "volatility_bucket": str,
            "trend_bucket": str,
            "liquidity_bucket": str
        }
        """

        state = self.build_market_state(trade_record)

        reward = self.rl_agent.compute_reward(trade_record)

        next_state = state  # simplified transition (can enhance later)

        action = trade_record.get("action")

        self.rl_agent.update_q_value(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state
        )

        # update performance analytics
        self.performance_tracker.update_strategy_metrics(
            trade_record.get("strategy"),
            trade_record
        )

        self.last_update_time = datetime.now()

    # ---------- HEALTH ----------
    def learning_status(self):

        return {
            "last_learning_update": self.last_update_time,
            "learning_active": True
        }