from datetime import datetime


class EnsembleVotingEngine:

    def __init__(self, config: dict):
        self.config = config
        self.strategy_weights = config.get("strategy_weights", {})
        self.min_confidence = config.get("min_confidence", 0.6)

    # ---------- CORE FUSION ----------
    def evaluate_signals(self, signals: list):

        """
        Input → list of strategy signals
        Output → final executable signal
        """

        if not signals:
            return None

        weighted_votes = []
        buy_score = 0
        sell_score = 0
        premium_sell_score = 0

        for signal in signals:

            strat = signal["strategy"]
            weight = self.strategy_weights.get(strat, 1)

            adjusted_conf = signal["confidence"] * weight

            weighted_votes.append((signal, adjusted_conf))

            if signal["direction"] == "BUY":
                buy_score += adjusted_conf

            elif signal["direction"] == "SELL":
                sell_score += adjusted_conf

            elif signal["direction"] == "SELL_PREMIUM":
                premium_sell_score += adjusted_conf

        # ---------- DECISION LOGIC ----------
        decision_direction = None
        decision_strength = max(buy_score, sell_score, premium_sell_score)

        if decision_strength < self.min_confidence:
            return None

        if buy_score == decision_strength:
            decision_direction = "BUY"

        elif sell_score == decision_strength:
            decision_direction = "SELL"

        else:
            decision_direction = "SELL_PREMIUM"

        # pick highest contributing signal
        best_signal = max(weighted_votes, key=lambda x: x[1])[0]

        final_signal = {
            "symbol": best_signal["symbol"],
            "direction": decision_direction,
            "confidence": decision_strength,
            "entry_price": best_signal["entry_price"],
            "stoploss": best_signal["stoploss"],
            "target": best_signal["target"],
            "strategy_source": best_signal["strategy"],
            "timestamp": datetime.now()
        }

        return final_signal