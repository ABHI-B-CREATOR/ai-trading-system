from datetime import datetime
from strategy_base_class import StrategyBase


class OptionWritingEngine(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        config = config or {}
        strategy_name = config.get("strategy_name", "OptionWritingEngine")
        
        super().__init__(
            name=strategy_name,
            broadcast_service=broadcast_service,
            notification_service=notification_service
        )
        
        self.config = config
        self.notification_service = notification_service
        self.strategy_name = strategy_name

        self.atm_iv = None
        self.iv_percentile = None
        self.iv_trend = None
        self.market_momentum = None
        self.liquidity_score = None
        self.last_price = None
        self.theta_window = None

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")

    def on_candle(self, candle_data: dict):
        self.market_momentum = candle_data.get("momentum_slope")

    def on_option_chain(self, option_data: dict):
        self.atm_iv = option_data.get("atm_iv")
        self.iv_percentile = option_data.get("iv_percentile")
        self.iv_trend = option_data.get("iv_trend")
        self.liquidity_score = option_data.get("liquidity_score")
        self.theta_window = option_data.get("theta_window")

    # ===== MARKET DATA ROUTER =====
    def on_market_data(self, tick_data: dict):
        """Route incoming market data to appropriate handlers"""
        self.on_tick(tick_data)
        signal = self.generate_signal()
        if signal:
            self.broadcast_signal(signal)
    def generate_signal(self):

        if None in [self.atm_iv,
                    self.iv_percentile,
                    self.iv_trend,
                    self.market_momentum,
                    self.liquidity_score,
                    self.theta_window,
                    self.last_price]:
            return None

        # Use .get() with sensible defaults
        ivp_threshold = self.config.get("ivp_threshold", 60)
        momentum_neutral_threshold = self.config.get("momentum_neutral_threshold", 0.5)
        liq_threshold = self.config.get("liq_threshold", 50)
        premium_sl_pct = self.config.get("premium_sl_pct", 1.02)
        premium_decay_target_pct = self.config.get("premium_decay_target_pct", 0.97)
        symbol = self.config.get("symbol", "UNKNOWN")

        # PREMIUM SELLING ENVIRONMENT
        if (self.iv_percentile > ivp_threshold and
                self.iv_trend == "FALLING" and
                abs(self.market_momentum) < momentum_neutral_threshold and
                self.liquidity_score > liq_threshold and
                self.theta_window):

            signal = {
                "symbol": symbol,
                "direction": "SELL_PREMIUM",
                "confidence": min(0.75 + self.iv_percentile * 0.002, 0.97),
                "entry_price": self.last_price,
                "stoploss": self.last_price * premium_sl_pct,
                "target": self.last_price * premium_decay_target_pct,
                "strategy": self.strategy_name,
                "timestamp": datetime.now()
            }

            self.last_signal_time = datetime.now()
            return self.risk_filter(signal)

        return None