import random
import time
from datetime import datetime
import json


class DemoMarketDataGenerator:
    """Generates simulated market data for demo/testing purposes"""
    
    def __init__(self, symbols=None):
        self.symbols = symbols or ["BANKNIFTY", "NIFTY", "FINNIFTY"]
        self.prices = {symbol: 50000 + random.randint(-1000, 1000) for symbol in self.symbols}
        self.volatilities = {symbol: random.uniform(15, 30) for symbol in self.symbols}
        
    def get_tick(self):
        """Generate a single market tick"""
        symbol = random.choice(self.symbols)
        
        # Simulate price movement (±0.2%)
        price_change = random.uniform(-0.002, 0.002)
        self.prices[symbol] *= (1 + price_change)
        
        return {
            "symbol": symbol,
            "price": round(self.prices[symbol], 2),
            "bid": round(self.prices[symbol] - 0.5, 2),
            "ask": round(self.prices[symbol] + 0.5, 2),
            "volume": random.randint(1000, 10000),
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def get_market_snapshot(self):
        """Get snapshot of all symbols"""
        return {
            symbol: {
                "price": round(self.prices[symbol], 2),
                "bid": round(self.prices[symbol] - 0.5, 2),
                "ask": round(self.prices[symbol] + 0.5, 2),
                "volatility": round(self.volatilities[symbol], 2),
                "change": round(random.uniform(-2, 2), 2),
                "timestamp": datetime.utcnow().isoformat()
            }
            for symbol in self.symbols
        }
    
    def get_strategy_signal(self):
        """Generate simulated strategy signal"""
        return {
            "strategy": random.choice(["trend", "breakout", "scalper", "range_decay", "option_writer", "vol_expansion"]),
            "symbol": random.choice(self.symbols),
            "action": random.choice(["BUY", "SELL", "HOLD"]),
            "confidence": round(random.uniform(0.5, 1.0), 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_pnl_update(self, current_pnl=0):
        """Generate simulated P&L update"""
        pnl_change = random.uniform(-100, 100)
        new_pnl = current_pnl + pnl_change
        
        return {
            "pnl": round(new_pnl, 2),
            "daily_change": round(pnl_change, 2),
            "win_rate": round(random.uniform(0.45, 0.65), 2),
            "trades_today": random.randint(0, 20),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global demo generator instance
_demo_generator = None


def get_demo_generator(symbols=None):
    """Get or create the global demo data generator"""
    global _demo_generator
    if _demo_generator is None:
        _demo_generator = DemoMarketDataGenerator(symbols)
    return _demo_generator
