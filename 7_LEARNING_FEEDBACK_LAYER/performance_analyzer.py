import pandas as pd
from datetime import datetime


class PerformanceAnalyzer:

    def __init__(self):

        self.trade_history = []
        self.strategy_metrics = {}
        self.trade_logger = None  # ===== TRADE LOGGER INJECTION =====

    # ---------- ADD TRADE ----------
    def record_trade(self, trade_record: dict):

        self.trade_history.append(trade_record)

        strategy = trade_record.get("strategy")

        if strategy not in self.strategy_metrics:
            self.strategy_metrics[strategy] = {
                "trades": 0,
                "wins": 0,
                "pnl": 0
            }

        self.strategy_metrics[strategy]["trades"] += 1
        self.strategy_metrics[strategy]["pnl"] += trade_record.get("pnl", 0)

        if trade_record.get("pnl", 0) > 0:
            self.strategy_metrics[strategy]["wins"] += 1

    # ---------- WIN RATE ----------
    def win_rate(self):

        total = len(self.trade_history)

        if total == 0:
            return 0

        wins = sum(1 for t in self.trade_history if t.get("pnl", 0) > 0)

        return wins / total * 100

    # ---------- EXPECTANCY ----------
    def expectancy(self):

        if not self.trade_history:
            return 0

        pnl_series = [t.get("pnl", 0) for t in self.trade_history]

        avg_win = pd.Series([p for p in pnl_series if p > 0]).mean()
        avg_loss = pd.Series([p for p in pnl_series if p <= 0]).mean()

        win_rate = self.win_rate() / 100

        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        return expectancy

    # ---------- EQUITY CURVE ----------
    def equity_curve(self):

        equity = 0
        curve = []

        for t in self.trade_history:
            equity += t.get("pnl", 0)
            curve.append(equity)

        return curve

    # ---------- STRATEGY SUMMARY ----------
    def strategy_summary(self):

        summary = {}

        for strat, data in self.strategy_metrics.items():

            trades = data["trades"]
            wins = data["wins"]

            win_rate = (wins / trades * 100) if trades else 0

            summary[strat] = {
                "trades": trades,
                "win_rate": win_rate,
                "total_pnl": data["pnl"]
            }

        return summary

    # ---------- DASHBOARD SNAPSHOT ----------
    def performance_snapshot(self):

        return {
            "total_trades": len(self.trade_history),
            "win_rate": self.win_rate(),
            "expectancy": self.expectancy(),
            "timestamp": datetime.now()
        }

    # -------------------------------------------------
    # TRADE LOGGER INTEGRATION
    # -------------------------------------------------

    def attach_trade_logger(self, trade_logger):
        """Attach trade logger for learning feedback"""
        self.trade_logger = trade_logger
        print("🔗 Trade Logger Attached To Performance Analyzer")

    def get_equity_curve(self):
        """Generate equity curve from trade logger"""
        if not self.trade_logger or not hasattr(self.trade_logger, 'trades'):
            return []

        pnl = 0
        curve = []

        # Use recent trades from logger
        trades = self.trade_logger.get_all_trades()

        for trade in trades:
            # Simplified - use qty as proxy for profit
            qty = trade.get("qty", 1)
            pnl += qty
            curve.append(pnl)

        return curve

    def get_live_metrics(self):
        """Get live metrics from connected trade logger"""
        if not self.trade_logger:
            return {}

        trades = self.trade_logger.get_recent_trades(n=100)

        return {
            "recent_trades": len(trades),
            "last_trade": trades[-1] if trades else None,
            "trades_available": len(self.trade_logger.get_all_trades())
        }

    def get_strategy_metrics(self):
        """
        Get metrics for all strategies.
        Returns dict with strategy names as keys and metrics as values.
        """
        # Build metrics from strategy_metrics and trade_history
        metrics = {}
        
        for strategy, data in self.strategy_metrics.items():
            trades = data.get("trades", 0)
            wins = data.get("wins", 0)
            pnl = data.get("pnl", 0)
            
            win_rate = (wins / trades * 100) if trades > 0 else 0
            avg_pnl = (pnl / trades) if trades > 0 else 0
            
            metrics[strategy] = {
                "trades": trades,
                "wins": wins,
                "losses": trades - wins,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(pnl, 2),
                "avg_pnl": round(avg_pnl, 2),
                "active": True  # Could be enhanced to track active state
            }
        
        # If no metrics yet, return empty dict with placeholder
        if not metrics:
            return {
                "TrendStrategy": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True},
                "BreakoutStrategy": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True},
                "MomentumScalper": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True},
                "RangeDecay": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True},
                "OptionWriter": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True},
                "VolExpansion": {"trades": 0, "win_rate": 0, "total_pnl": 0, "active": True}
            }
        
        return metrics