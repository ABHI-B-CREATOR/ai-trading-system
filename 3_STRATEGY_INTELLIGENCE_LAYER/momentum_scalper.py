from datetime import datetime
from strategy_base_class import StrategyBase


class MomentumScalper(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        config = config or {}
        strategy_name = config.get("strategy_name", "MomentumScalper")
        
        super().__init__(
            name=strategy_name,
            broadcast_service=broadcast_service,
            notification_service=notification_service
        )
        
        self.config = config
        self.notification_service = notification_service
        self.strategy_name = strategy_name

        self.last_price = None
        self.price_velocity = None
        self.volume_burst = False
        self.orderflow_imbalance = None
        self.rsi_fast = None
        self.spread = None

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")
        self.price_velocity = tick_data.get("price_velocity")
        self.spread = tick_data.get("spread")

    def on_candle(self, candle_data: dict):
        self.volume_burst = candle_data.get("volume_burst", False)
        self.rsi_fast = candle_data.get("rsi_fast")

    def on_option_chain(self, option_data: dict):
        self.orderflow_imbalance = option_data.get("orderflow_imbalance")

    # ===== MARKET DATA ROUTER =====
    def on_market_data(self, tick_data: dict):
        """Route incoming market data to appropriate handlers"""
        self.on_tick(tick_data)
        signal = self.generate_signal()
        if signal:
            self.broadcast_signal(signal)

    # ---------- SIGNAL ENGINE ----------
    def generate_signal(self):
        """
        Generate scalping signal with relaxed conditions for live testing.
        """
        if self.last_price is None:
            return None

        # Get config with defaults
        velocity_threshold = self.config.get("velocity_threshold", 0.001)
        imbalance_threshold = self.config.get("imbalance_threshold", 0.3)
        max_spread = self.config.get("max_spread", 5)
        scalp_sl_pct = self.config.get("scalp_sl_pct", 0.003)
        scalp_tg_pct = self.config.get("scalp_tg_pct", 0.005)
        symbol = self.config.get("symbol", "BANKNIFTY")

        # Use defaults if data not available
        price_velocity = self.price_velocity or 0
        orderflow_imbalance = self.orderflow_imbalance or 1.0
        rsi_fast = self.rsi_fast or 50
        spread = self.spread or 1
        volume_burst = self.volume_burst

        # Calculate momentum score
        momentum_score = 50  # Neutral baseline
        
        # Velocity contribution
        if price_velocity > velocity_threshold:
            momentum_score += min(20, price_velocity * 1000)
        elif price_velocity < -velocity_threshold:
            momentum_score -= min(20, abs(price_velocity) * 1000)
            
        # RSI contribution
        if rsi_fast > 60:
            momentum_score += (rsi_fast - 60) / 2
        elif rsi_fast < 40:
            momentum_score -= (40 - rsi_fast) / 2
            
        # Orderflow contribution
        if orderflow_imbalance > 1.2:
            momentum_score += 10
        elif orderflow_imbalance < 0.8:
            momentum_score -= 10
            
        # Volume burst adds conviction
        if volume_burst:
            momentum_score += 10 if momentum_score > 50 else -10

        # LONG SCALP
        if momentum_score >= 62 and spread < max_spread:
            confidence = min(0.90, 0.5 + (momentum_score - 50) / 100)
            signal = {
                "symbol": symbol,
                "direction": "BUY",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": self.last_price * (1 - scalp_sl_pct),
                "target": self.last_price * (1 + scalp_tg_pct),
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "momentum_score": momentum_score
            }
            self.last_signal_time = datetime.now()
            return signal

        # SHORT SCALP
        if momentum_score <= 38 and spread < max_spread:
            confidence = min(0.90, 0.5 + (50 - momentum_score) / 100)
            signal = {
                "symbol": symbol,
                "direction": "SELL",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": self.last_price * (1 + scalp_sl_pct),
                "target": self.last_price * (1 - scalp_tg_pct),
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "momentum_score": momentum_score
            }
            self.last_signal_time = datetime.now()
            return signal

        return None