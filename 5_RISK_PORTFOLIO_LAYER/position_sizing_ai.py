class PositionSizingAI:

    def __init__(self, config: dict):

        self.max_risk_per_trade = config.get("max_risk_per_trade_pct", 1.0)
        self.max_capital_allocation = config.get("max_capital_allocation_pct", 20)
        self.volatility_position_reduce = config.get("volatility_reduce_factor", 0.7)

    # ---------- BASE POSITION SIZE ----------
    def calculate_base_size(self, capital: float, stoploss_points: float):

        if stoploss_points <= 0:
            return 0

        risk_amount = capital * (self.max_risk_per_trade / 100)

        qty = risk_amount / stoploss_points

        return max(qty, 0)

    # ---------- CONFIDENCE SCALING ----------
    def adjust_for_confidence(self, qty: float, confidence: float):

        return qty * confidence

    # ---------- VOLATILITY ADJUSTMENT ----------
    def adjust_for_volatility(self, qty: float, market_state: dict):

        vol = market_state.get("volatility_level")

        if vol == "HIGH":
            return qty * self.volatility_position_reduce

        elif vol == "LOW":
            return qty * 1.1

        return qty

    # ---------- PORTFOLIO CAP ----------
    def enforce_portfolio_limit(self, qty: float,
                                price: float,
                                capital: float):

        max_value = capital * (self.max_capital_allocation / 100)

        if qty * price > max_value:
            qty = max_value / price

        return qty

    # ---------- MASTER SIZING ----------
    def compute_position_size(self,
                              signal: dict,
                              capital: float,
                              market_state: dict):

        stoploss_points = abs(
            signal["entry_price"] - signal["stoploss"]
        )

        qty = self.calculate_base_size(capital, stoploss_points)

        qty = self.adjust_for_confidence(qty, signal["confidence"])

        qty = self.adjust_for_volatility(qty, market_state)

        qty = self.enforce_portfolio_limit(
            qty,
            signal["entry_price"],
            capital
        )

        return int(qty)