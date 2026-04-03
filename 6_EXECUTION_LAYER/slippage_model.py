class SlippageModel:

    def __init__(self, config: dict):

        self.base_slippage_pct = config.get("base_slippage_pct", 0.02)
        self.volatility_impact_factor = config.get("volatility_impact_factor", 1.5)
        self.liquidity_impact_factor = config.get("liquidity_impact_factor", 1.2)
        self.max_allowed_slippage = config.get("max_allowed_slippage_pct", 0.5)

    # ---------- VOLATILITY IMPACT ----------
    def volatility_adjustment(self, atr: float, price: float):

        if price == 0:
            return 0

        vol_pct = atr / price * 100
        return vol_pct * self.volatility_impact_factor

    # ---------- LIQUIDITY IMPACT ----------
    def liquidity_adjustment(self, market_depth: dict):

        spread = market_depth.get("spread", 0)
        depth_score = market_depth.get("depth_score", 1)

        if depth_score <= 0:
            depth_score = 0.5

        return spread * self.liquidity_impact_factor / depth_score

    # ---------- TOTAL SLIPPAGE ----------
    def estimate_slippage(self, signal: dict,
                          market_depth: dict,
                          atr: float):

        price = signal["entry_price"]

        base = self.base_slippage_pct
        vol_adj = self.volatility_adjustment(atr, price)
        liq_adj = self.liquidity_adjustment(market_depth)

        total_slippage = base + vol_adj + liq_adj

        return total_slippage

    # ---------- TRADE FILTER ----------
    def allow_trade(self, estimated_slippage: float):

        if estimated_slippage > self.max_allowed_slippage:
            return False

        return True