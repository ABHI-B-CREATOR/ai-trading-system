class CapitalAllocator:

    def __init__(self, config: dict):

        self.total_capital = config.get("initial_capital", 0)

        # base allocation per strategy
        self.base_allocations = config.get("strategy_capital_weights", {})

        # performance memory
        self.strategy_performance = {}

        self.max_strategy_cap_pct = config.get("max_strategy_cap_pct", 30)

    # ---------- UPDATE PERFORMANCE ----------
    def update_performance(self, strategy: str, pnl: float):

        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = 0

        self.strategy_performance[strategy] += pnl

    # ---------- PERFORMANCE FACTOR ----------
    def performance_factor(self, strategy: str):

        pnl = self.strategy_performance.get(strategy, 0)

        if pnl > 0:
            return 1.2

        elif pnl < 0:
            return 0.7

        return 1.0

    # ---------- ALLOCATION CALCULATOR ----------
    def allocate(self, strategy: str):

        base_weight = self.base_allocations.get(strategy, 1)

        perf_factor = self.performance_factor(strategy)

        allocation_pct = base_weight * perf_factor

        allocation_pct = min(allocation_pct, self.max_strategy_cap_pct)

        capital_allocated = self.total_capital * allocation_pct / 100

        return capital_allocated

    # ---------- PORTFOLIO SUMMARY ----------
    def portfolio_view(self):

        return {
            "total_capital": self.total_capital,
            "strategy_performance": self.strategy_performance
        }