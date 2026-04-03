class ExposureManager:

    def __init__(self, config: dict):

        self.max_directional_exposure = config.get(
            "max_directional_exposure_pct", 60
        )

        self.max_symbol_exposure = config.get(
            "max_symbol_exposure_pct", 40
        )

        self.max_premium_sell_exposure = config.get(
            "max_premium_sell_pct", 50
        )

        self.current_positions = []

    # ---------- ADD POSITION ----------
    def register_position(self, position: dict):
        """
        position example:
        {
            "symbol": str,
            "direction": "BUY"/"SELL"/"SELL_PREMIUM",
            "notional_value": float
        }
        """
        self.current_positions.append(position)

    # ---------- EXPOSURE CALCULATIONS ----------
    def directional_exposure(self):

        buy_val = sum(
            p["notional_value"]
            for p in self.current_positions
            if p["direction"] == "BUY"
        )

        sell_val = sum(
            p["notional_value"]
            for p in self.current_positions
            if p["direction"] == "SELL"
        )

        total = buy_val + sell_val

        if total == 0:
            return 0

        return max(buy_val, sell_val) / total * 100

    def symbol_exposure(self, symbol: str):

        sym_val = sum(
            p["notional_value"]
            for p in self.current_positions
            if p["symbol"] == symbol
        )

        total = sum(p["notional_value"] for p in self.current_positions)

        if total == 0:
            return 0

        return sym_val / total * 100

    def premium_sell_exposure(self):

        prem_val = sum(
            p["notional_value"]
            for p in self.current_positions
            if p["direction"] == "SELL_PREMIUM"
        )

        total = sum(p["notional_value"] for p in self.current_positions)

        if total == 0:
            return 0

        return prem_val / total * 100

    # ---------- TRADE ALLOW CHECK ----------
    def allow_trade(self, new_position: dict):

        temp_positions = self.current_positions + [new_position]

        self.current_positions = temp_positions

        dir_exp = self.directional_exposure()
        sym_exp = self.symbol_exposure(new_position["symbol"])
        prem_exp = self.premium_sell_exposure()

        # rollback temp add
        self.current_positions.pop()

        if dir_exp > self.max_directional_exposure:
            return False

        if sym_exp > self.max_symbol_exposure:
            return False

        if prem_exp > self.max_premium_sell_exposure:
            return False

        return True

    # ---------- PORTFOLIO SNAPSHOT ----------
    def exposure_snapshot(self):

        return {
            "directional_exposure_pct": self.directional_exposure(),
            "premium_sell_exposure_pct": self.premium_sell_exposure(),
            "total_positions": len(self.current_positions)
        }