from datetime import datetime
from strategy_base_class import StrategyBase


class RangeDecayStrategy(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        config = config or {}
        strategy_name = config.get("strategy_name", "RangeDecayStrategy")
        
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
        self.atr = None
        self.iv = None
        self.iv_trend = None
        self.range_stability = None

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")

    def on_candle(self, candle_data: dict):
        self.range_high = candle_data.get("range_high")
        self.range_low = candle_data.get("range_low")
        self.atr = candle_data.get("atr")

    def on_option_chain(self, option_data: dict):
        self.iv = option_data.get("atm_iv")
        self.iv_trend = option_data.get("iv_trend")
        self.range_stability = option_data.get("range_stability_score")

    # ===== MARKET DATA ROUTER =====
    def on_market_data(self, tick_data: dict):
        """Route incoming market data to appropriate handlers"""
        self.on_tick(tick_data)
        signal = self.generate_signal()
        if signal:
            self.broadcast_signal(signal)
    def generate_signal(self):

        if None in [self.range_high, self.range_low,
                    self.last_price, self.atr,
                    self.iv, self.iv_trend,
                    self.range_stability]:
            return None

        mid_range = (self.range_high + self.range_low) / 2
        range_width = self.range_high - self.range_low

        # Use .get() with sensible defaults
        atr_contract_threshold = self.config.get("atr_contract_threshold", 50)
        iv_sell_threshold = self.config.get("iv_sell_threshold", 15)
        stability_threshold = self.config.get("stability_threshold", 0.6)
        range_sl_factor = self.config.get("range_sl_factor", 0.5)
        decay_target_factor = self.config.get("decay_target_factor", 0.3)
        symbol = self.config.get("symbol", "UNKNOWN")

        # SHORT STRANGLE / IRON CONDOR ENVIRONMENT
        if (self.range_low < self.last_price < self.range_high and
                self.atr < atr_contract_threshold and
                self.iv > iv_sell_threshold and
                self.iv_trend == "FALLING" and
                self.range_stability > stability_threshold):

            signal = {
                "symbol": symbol,
                "direction": "SELL_PREMIUM",
                "confidence": min(0.7 + self.range_stability * 0.1, 0.96),
                "entry_price": mid_range,
                "stoploss": range_width * range_sl_factor,
                "target": range_width * decay_target_factor,
                "strategy": self.strategy_name,
                "timestamp": datetime.now()
            }

            self.last_signal_time = datetime.now()
            return self.risk_filter(signal)

        return None