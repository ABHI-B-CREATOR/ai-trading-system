import numpy as np
from collections import defaultdict


class ReinforcementAgent:

    def __init__(self, config: dict):

        self.alpha = config.get("learning_rate", 0.1)
        self.gamma = config.get("discount_factor", 0.9)
        self.epsilon = config.get("exploration_rate", 0.1)

        # Q-table → state-action value store
        self.q_table = defaultdict(lambda: defaultdict(float))

    # ---------- STATE BUILDER ----------
    def build_state(self, market_features: dict):

        """
        Convert feature dict into discrete state tuple
        """

        state = (
            market_features.get("regime"),
            market_features.get("vol_bucket"),
            market_features.get("trend_strength_bucket"),
            market_features.get("liquidity_bucket")
        )

        return state

    # ---------- ACTION SELECTION ----------
    def select_action(self, state, possible_actions):

        if np.random.rand() < self.epsilon:
            return np.random.choice(possible_actions)

        q_vals = self.q_table[state]
        return max(possible_actions, key=lambda a: q_vals[a])

    # ---------- LEARNING UPDATE ----------
    def update_q_value(self, state, action, reward, next_state):

        max_next_q = max(self.q_table[next_state].values(), default=0)

        current_q = self.q_table[state][action]

        new_q = current_q + self.alpha * (
            reward + self.gamma * max_next_q - current_q
        )

        self.q_table[state][action] = new_q

    # ---------- REWARD FUNCTION ----------
    def compute_reward(self, trade_result: dict):

        """
        trade_result example:
        {
            "pnl": float,
            "drawdown": float,
            "holding_time": int
        }
        """

        pnl = trade_result.get("pnl", 0)
        drawdown = trade_result.get("drawdown", 0)
        holding = trade_result.get("holding_time", 1)

        reward = pnl - (drawdown * 0.5) - (holding * 0.01)

        return reward