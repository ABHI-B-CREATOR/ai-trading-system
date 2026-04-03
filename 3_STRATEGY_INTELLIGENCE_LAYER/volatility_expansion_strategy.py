from datetime import datetime
from strategy_base_class import StrategyBase


class VolatilityExpansionStrategy(StrategyBase):

    def __init__(self, config=None, broadcast_service=None, notification_service=None):
        config = config or {}
        strategy_name = config.get("strategy_name", "VolatilityExpansionStrategy")
        
        super().__init__(
            name=strategy_name,
            broadcast_service=broadcast_service,
            notification_service=notification_service
        )
        
        self.config = config
        self.notification_service = notification_service
        self.strategy_name = strategy_name

        self.last_price = None
        self.atr = None
        self.prev_atr = None
        self.bb_width = None
        self.prev_bb_width = None
        self.iv = None
        self.iv_change = None
        self.regime_shift = None
        self.breakout_level = None

    # ---------- DATA INPUT ----------
    def on_tick(self, tick_data: dict):
        self.last_price = tick_data.get("ltp")

    def on_candle(self, candle_data: dict):
        self.atr = candle_data.get("atr")
        self.prev_atr = candle_data.get("prev_atr")
        self.bb_width = candle_data.get("bb_width")
        self.prev_bb_width = candle_data.get("prev_bb_width")
        self.breakout_level = candle_data.get("compression_breakout")

    def on_option_chain(self, option_data: dict):
        self.iv = option_data.get("atm_iv")
        self.iv_change = option_data.get("iv_change")
        self.regime_shift = option_data.get("regime_shift")

    # ===== MARKET DATA ROUTER =====
    def on_market_data(self, tick_data: dict):
        """Route incoming market data to appropriate handlers"""
        self.on_tick(tick_data)
        signal = self.generate_signal()
        if signal:
            self.broadcast_signal(signal)
    def generate_signal(self):

        if None in [self.last_price,
                    self.atr,
                    self.prev_atr,
                    self.bb_width,
                    self.prev_bb_width,
                    self.iv_change,
                    self.regime_shift,
                    self.breakout_level]:
            return None

        # Use .get() with sensible defaults
        atr_expansion_factor = self.config.get("atr_expansion_factor", 1.2)
        bb_expansion_factor = self.config.get("bb_expansion_factor", 1.2)
        iv_impulse_threshold = self.config.get("iv_impulse_threshold", 0.05)
        sl_atr_factor = self.config.get("sl_atr_factor", 1.5)
        tg_atr_factor = self.config.get("tg_atr_factor", 2.0)
        symbol = self.config.get("symbol", "UNKNOWN")
        
        atr_expansion = self.atr > self.prev_atr * atr_expansion_factor
        bb_expansion = self.bb_width > self.prev_bb_width * bb_expansion_factor

        # VOLATILITY UPSIDE EXPANSION
        if (atr_expansion and
                bb_expansion and
                self.iv_change > iv_impulse_threshold and
                self.regime_shift == "VOL_EXPANSION" and
                self.last_price > self.breakout_level):

            signal = {
                "symbol": symbol,
                "direction": "BUY",
                "confidence": min(0.7 + self.iv_change * 0.2, 0.98),
                "entry_price": self.last_price,
                "stoploss": self.last_price - self.atr * sl_atr_factor,
                "target": self.last_price + self.atr * tg_atr_factor,
                "strategy": self.strategy_name,
                "timestamp": datetime.now()
            }

            self.last_signal_time = datetime.now()
            return self.risk_filter(signal)

        # VOLATILITY DOWNSIDE EXPANSION
        if (atr_expansion and
                bb_expansion and
                self.iv_change > iv_impulse_threshold and
                self.regime_shift == "VOL_EXPANSION" and
                self.last_price < self.breakout_level):

            signal = {
                "symbol": symbol,
                "direction": "SELL",
                "confidence": min(0.7 + self.iv_change * 0.2, 0.98),
                "entry_price": self.last_price,
                "stoploss": self.last_price + self.atr * sl_atr_factor,
                "target": self.last_price - self.atr * tg_atr_factor,
                "strategy": self.strategy_name,
                "timestamp": datetime.now()
            }

            self.last_signal_time = datetime.now()
            return self.risk_filter(signal)

        return None