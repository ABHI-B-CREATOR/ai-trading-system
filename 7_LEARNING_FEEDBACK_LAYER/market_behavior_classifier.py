class MarketBehaviorClassifier:

    def __init__(self, config: dict):

        self.trend_threshold = config.get("trend_strength_threshold", 0.6)
        self.volatility_panic_atr = config.get("panic_atr_threshold", 1.8)
        self.liquidity_vacuum_threshold = config.get(
            "liquidity_vacuum_depth", 50
        )
        self.squeeze_bb_threshold = config.get(
            "squeeze_bb_width", 0.8
        )

    # ---------- TREND DETECTION ----------
    def is_trending(self, features: dict):

        trend_strength = features.get("trend_strength_score", 0)

        return trend_strength >= self.trend_threshold

    # ---------- PANIC VOLATILITY ----------
    def is_panic(self, features: dict):

        atr_ratio = features.get("atr_ratio", 1)

        return atr_ratio >= self.volatility_panic_atr

    # ---------- LIQUIDITY VACUUM ----------
    def is_liquidity_vacuum(self, features: dict):

        depth = features.get("top5_depth", 100)

        return depth <= self.liquidity_vacuum_threshold

    # ---------- VOLATILITY SQUEEZE ----------
    def is_squeeze(self, features: dict):

        bb_width = features.get("bb_width", 1)

        return bb_width <= self.squeeze_bb_threshold

    # ---------- MASTER CLASSIFIER ----------
    def classify(self, features: dict):

        if self.is_panic(features):
            return "VOLATILITY_PANIC"

        if self.is_liquidity_vacuum(features):
            return "LIQUIDITY_VACUUM"

        if self.is_trending(features):
            return "TRENDING"

        if self.is_squeeze(features):
            return "VOL_SQUEEZE"

        return "RANGE_BOUND"

    # ---------- ENCODED STATE ----------
    def encoded_state(self, behavior: str):

        mapping = {
            "TRENDING": 1,
            "VOLATILITY_PANIC": 2,
            "LIQUIDITY_VACUUM": 3,
            "VOL_SQUEEZE": 4,
            "RANGE_BOUND": 0
        }

        return mapping.get(behavior, 0)