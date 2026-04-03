class StoplossOptimizer:

    def __init__(self, config: dict):

        self.atr_multiplier = config.get("atr_sl_multiplier", 1.5)
        self.tight_sl_factor = config.get("range_tight_sl_factor", 0.7)
        self.trend_sl_buffer = config.get("trend_sl_buffer", 1.2)

    # ---------- ATR BASED STOPLOSS ----------
    def atr_based_sl(self, entry_price: float,
                     direction: str,
                     atr: float):

        if direction == "BUY":
            return entry_price - atr * self.atr_multiplier

        elif direction == "SELL":
            return entry_price + atr * self.atr_multiplier

        return entry_price

    # ---------- RANGE MARKET TIGHTEN ----------
    def tighten_in_range(self, sl: float,
                         entry_price: float,
                         direction: str):

        distance = abs(entry_price - sl) * self.tight_sl_factor

        if direction == "BUY":
            return entry_price - distance

        elif direction == "SELL":
            return entry_price + distance

        return sl

    # ---------- TREND MARKET BUFFER ----------
    def widen_in_trend(self, sl: float,
                       entry_price: float,
                       direction: str):

        distance = abs(entry_price - sl) * self.trend_sl_buffer

        if direction == "BUY":
            return entry_price - distance

        elif direction == "SELL":
            return entry_price + distance

        return sl

    # ---------- MASTER OPTIMIZER ----------
    def optimize_stoploss(self,
                          signal: dict,
                          market_state: dict,
                          atr: float):

        sl = self.atr_based_sl(
            signal["entry_price"],
            signal["direction"],
            atr
        )

        regime = market_state.get("regime")

        if regime == "SIDEWAYS":
            sl = self.tighten_in_range(
                sl,
                signal["entry_price"],
                signal["direction"]
            )

        elif regime == "TRENDING":
            sl = self.widen_in_trend(
                sl,
                signal["entry_price"],
                signal["direction"]
            )

        return sl