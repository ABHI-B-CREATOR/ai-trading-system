from datetime import datetime
from strategy_base_class import StrategyBase


class BreakoutStrategy(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        config = config or {}
        strategy_name = config.get("strategy_name", "BreakoutStrategy")
        
        super().__init__(
            name=strategy_name,
            broadcast_service=broadcast_service,
            notification_service=notification_service
        )
        
        self.config = config
        self.notification_service = notification_service
        self.strategy_name = strategy_name

        self.range_high = None
        self.range_low = None
        self.last_price = None
        self.volume_spike = False
        self.atr = None
        self.liquidity_score = None

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")

    def on_candle(self, candle_data: dict):
        self.range_high = candle_data.get("range_high")
        self.range_low = candle_data.get("range_low")
        self.atr = candle_data.get("atr")
        self.volume_spike = candle_data.get("volume_spike", False)

    def on_option_chain(self, option_data: dict):
        self.liquidity_score = option_data.get("liquidity_score")

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
        Generate breakout signal with relaxed conditions for live testing.
        """
        # Require at least price
        if self.last_price is None:
            return None

        # Get config with defaults
        breakout_buffer = self.config.get("breakout_buffer", 10)
        atr_threshold = self.config.get("atr_threshold", 50)
        liq_threshold = self.config.get("liq_threshold", 30)
        rr_multiplier = self.config.get("rr_multiplier", 2.0)
        symbol = self.config.get("symbol", "BANKNIFTY")

        # Use defaults if data not available
        range_high = self.range_high or (self.last_price * 1.005)  # 0.5% above
        range_low = self.range_low or (self.last_price * 0.995)   # 0.5% below
        atr = self.atr or (self.last_price * 0.002)  # Default 0.2% ATR
        liquidity_score = self.liquidity_score or 50
        volume_spike = self.volume_spike

        # Calculate breakout score
        breakout_score = 50  # Neutral baseline
        
        # Check for upside breakout
        if self.last_price > range_high:
            distance_pct = (self.last_price - range_high) / range_high * 100
            breakout_score += min(25, distance_pct * 10)
            
        # Check for downside breakout  
        elif self.last_price < range_low:
            distance_pct = (range_low - self.last_price) / range_low * 100
            breakout_score -= min(25, distance_pct * 10)
        
        # Volume spike adds conviction
        if volume_spike:
            breakout_score += 15 if breakout_score > 50 else -15
            
        # ATR contribution
        if atr and atr > atr_threshold:
            breakout_score += 10 if breakout_score > 50 else -10

        # UPSIDE BREAKOUT
        if breakout_score >= 65:
            confidence = min(0.95, 0.5 + (breakout_score - 50) / 100)
            signal = {
                "symbol": symbol,
                "direction": "BUY",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": range_high,
                "target": self.last_price + atr * rr_multiplier,
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "breakout_score": breakout_score
            }
            self.last_signal_time = datetime.now()
            return signal

        # DOWNSIDE BREAKOUT
        if breakout_score <= 35:
            confidence = min(0.95, 0.5 + (50 - breakout_score) / 100)
            signal = {
                "symbol": symbol,
                "direction": "SELL",
                "confidence": confidence,
                "entry_price": self.last_price,
                "stoploss": range_low,
                "target": self.last_price - atr * rr_multiplier,
                "strategy": self.strategy_name,
                "timestamp": datetime.now(),
                "breakout_score": breakout_score
            }
            self.last_signal_time = datetime.now()
            return signal

        return None