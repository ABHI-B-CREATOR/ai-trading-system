from datetime import datetime
from strategy_base_class import StrategyBase


class TrendStrategy(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        # Extract strategy name and config
        config = config or {}
        strategy_name = config.get("strategy_name", "TrendStrategy")
        
        super().__init__(
            name=strategy_name,
            broadcast_service=broadcast_service,
            notification_service=notification_service
        )
        
        # Store config for use in signal generation
        self.config = config
        self.notification_service = notification_service

        self.fast_ema = None
        self.slow_ema = None
        self.vwap = None
        self.momentum = None
        self.regime = None
        self.last_price = None
        self.strategy_name = strategy_name

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")

    def on_candle(self, candle_data: dict):
        self.fast_ema = candle_data.get("ema_fast")
        self.slow_ema = candle_data.get("ema_slow")
        self.vwap = candle_data.get("vwap")
        self.momentum = candle_data.get("momentum_slope")

    def on_option_chain(self, option_data: dict):
        self.regime = option_data.get("market_regime")

    # ===== MARKET DATA ROUTER =====
    def on_market_data(self, tick_data: dict):
        """Route incoming market data to appropriate handlers"""
        self.on_tick(tick_data)
        signal = self.generate_signal()
        if signal:
            self.broadcast_signal(signal)
    def generate_signal(self):
        """
        Generate trading signal based on trend indicators.
        Relaxed conditions to generate signals more frequently for live testing.
        """
        # Require at least price and one indicator
        if self.last_price is None:
            return None

        # Get config with defaults
        momentum_threshold = self.config.get("momentum_threshold", 0.2)  # Relaxed from 0.5
        sl_pct = self.config.get("sl_pct", 0.01)  # 1% stop loss
        tg_pct = self.config.get("tg_pct", 0.02)  # 2% target
        symbol = self.config.get("symbol", "BANKNIFTY")

        # Use defaults if indicators not yet computed
        fast_ema = self.fast_ema or self.last_price
        slow_ema = self.slow_ema or self.last_price
        vwap = self.vwap or self.last_price
        momentum = self.momentum or 0
        regime = self.regime or "NEUTRAL"

        # Calculate trend score (0-100)
        trend_score = 50  # Neutral baseline
        
        # EMA crossover signals
        if fast_ema > slow_ema:
            trend_score += 15
        elif fast_ema < slow_ema:
            trend_score -= 15
            
        # Price vs VWAP
        if self.last_price > vwap:
            trend_score += 10
        elif self.last_price < vwap:
            trend_score -= 10
            
        # Momentum contribution
        if momentum and isinstance(momentum, (int, float)):
            trend_score += min(15, max(-15, momentum * 30))
            
        # Regime contribution
        if regime in ["TRENDING_UP", "UPTREND"]:
            trend_score += 10
        elif regime in ["TRENDING_DOWN", "DOWNTREND"]:
            trend_score -= 10

        # Generate BUY signal if score > 65
        if trend_score >= 65:
            confidence = min(0.95, 0.5 + (trend_score - 50) / 100)
            signal = {
                "symbol": symbol,
                "direction": "BUY",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": self.last_price * (1 - sl_pct),
                "target": self.last_price * (1 + tg_pct),
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "trend_score": trend_score,
                "indicators": {
                    "ema_fast": fast_ema,
                    "ema_slow": slow_ema,
                    "vwap": vwap,
                    "momentum": momentum,
                    "regime": regime
                }
            }
            self.last_signal_time = datetime.now()
            return signal

        # Generate SELL signal if score < 35
        if trend_score <= 35:
            confidence = min(0.95, 0.5 + (50 - trend_score) / 100)
            signal = {
                "symbol": symbol,
                "direction": "SELL",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": self.last_price * (1 + sl_pct),
                "target": self.last_price * (1 - tg_pct),
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "trend_score": trend_score,
                "indicators": {
                    "ema_fast": fast_ema,
                    "ema_slow": slow_ema,
                    "vwap": vwap,
                    "momentum": momentum,
                    "regime": regime
                }
            }
            self.last_signal_time = datetime.now()
            return signal

        return None