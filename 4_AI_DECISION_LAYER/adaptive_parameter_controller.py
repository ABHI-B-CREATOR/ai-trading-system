from datetime import datetime


class AdaptiveParameterController:

    def __init__(self, config: dict):

        self.config = config
        self.last_adjustment_time = None

    # ---------- VOLATILITY ADAPTATION ----------
    def adjust_for_volatility(self, strategy_config: dict, market_state: dict):

        vol = market_state.get("volatility_level")

        if vol == "HIGH":
            strategy_config["sl_pct"] *= 1.2
            strategy_config["tg_pct"] *= 1.4

        elif vol == "LOW":
            strategy_config["sl_pct"] *= 0.8
            strategy_config["tg_pct"] *= 0.9

        return strategy_config

    # ---------- DRAWDOWN ADAPTATION ----------
    def adjust_for_drawdown(self, strategy_config: dict, portfolio_state: dict):

        dd = portfolio_state.get("current_drawdown_pct", 0)

        if dd > self.config.get("drawdown_risk_reduce_level", 5):
            strategy_config["position_size_factor"] *= 0.7
            strategy_config["confidence_boost"] = 0.9

        return strategy_config

    # ---------- REGIME ADAPTATION ----------
    def adjust_for_market_regime(self, strategy_config: dict, market_state: dict):

        regime = market_state.get("regime")

        if regime == "TRENDING":
            strategy_config["momentum_threshold"] *= 0.9

        elif regime == "SIDEWAYS":
            strategy_config["momentum_threshold"] *= 1.2

        return strategy_config

    # ---------- MASTER CONTROL ----------
    def adapt_parameters(self, strategy_config: dict,
                         market_state: dict,
                         portfolio_state: dict):

        strategy_config = self.adjust_for_volatility(
            strategy_config, market_state
        )

        strategy_config = self.adjust_for_drawdown(
            strategy_config, portfolio_state
        )

        strategy_config = self.adjust_for_market_regime(
            strategy_config, market_state
        )

        self.last_adjustment_time = datetime.now()

        return strategy_config

    # ---------- HEALTH ----------
    def controller_status(self):

        return {
            "last_adjustment": self.last_adjustment_time,
            "adaptive_mode": True
        }