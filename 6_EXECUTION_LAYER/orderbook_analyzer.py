class OrderbookAnalyzer:

    def __init__(self, config: dict):

        self.imbalance_threshold = config.get("imbalance_threshold", 2.5)
        self.min_liquidity = config.get("min_top5_liquidity", 100)

    # ---------- LIQUIDITY SCORE ----------
    def liquidity_score(self, depth_data: dict):

        bids = depth_data.get("bids", [])
        asks = depth_data.get("asks", [])

        bid_liq = sum([b[1] for b in bids[:5]])
        ask_liq = sum([a[1] for a in asks[:5]])

        total = bid_liq + ask_liq

        if total == 0:
            return 0

        return total

    # ---------- IMBALANCE ----------
    def orderflow_imbalance(self, depth_data: dict):

        bids = depth_data.get("bids", [])
        asks = depth_data.get("asks", [])

        bid_liq = sum([b[1] for b in bids[:5]])
        ask_liq = sum([a[1] for a in asks[:5]])

        if ask_liq == 0:
            return 0

        imbalance = bid_liq / ask_liq

        return imbalance

    # ---------- EXECUTION BIAS ----------
    def execution_bias(self, depth_data: dict):

        imbalance = self.orderflow_imbalance(depth_data)

        if imbalance > self.imbalance_threshold:
            return "BUY_PRESSURE"

        elif imbalance < 1 / self.imbalance_threshold:
            return "SELL_PRESSURE"

        return "NEUTRAL"

    # ---------- LIQUIDITY FILTER ----------
    def allow_execution(self, depth_data: dict):

        score = self.liquidity_score(depth_data)

        if score < self.min_liquidity:
            return False

        return True

    # ---------- SNAPSHOT ----------
    def analyze(self, depth_data: dict):

        return {
            "liquidity_score": self.liquidity_score(depth_data),
            "imbalance": self.orderflow_imbalance(depth_data),
            "execution_bias": self.execution_bias(depth_data),
            "execution_allowed": self.allow_execution(depth_data)
        }