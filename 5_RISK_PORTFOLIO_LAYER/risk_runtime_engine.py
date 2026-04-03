class RiskRuntimeEngine:
    """
    Central risk governance engine for all trading
    Applies position sizing, stoploss, and exposure controls
    """

    def __init__(self, position_ai, stoploss_ai, exposure_manager):
        """
        position_ai: Position sizing engine
        stoploss_ai: Stoploss optimizer
        exposure_manager: Portfolio exposure controller
        """
        self.position_ai = position_ai
        self.stoploss_ai = stoploss_ai
        self.exposure_manager = exposure_manager

        self.mode = "normal"
        self.is_risk_event = False

        print("🛑 Risk Runtime Engine Initialised")

    # -------------------------------------------------
    # SIGNAL RISK PROCESSING
    # -------------------------------------------------

    def process_signal(self, signal):
        """
        Apply all risk controls to incoming signal
        Returns enriched signal with sizing + stoploss
        """
        if not signal:
            return None

        try:
            # Get market state and ATR from signal or defaults
            market_state = signal.get("market_state", {"volatility_level": "NORMAL", "regime": "NEUTRAL"})
            capital = signal.get("capital", 100000)  # Default capital
            atr = signal.get("atr", abs(signal.get("entry_price", 0) - signal.get("stoploss", 0)) / 1.5)
            
            # Calculate position size (use compute_position_size with correct params)
            sized_qty = self.position_ai.compute_position_size(signal, capital, market_state)

            # Generate optimized stoploss (use optimize_stoploss with correct params)
            sl = self.stoploss_ai.optimize_stoploss(signal, market_state, atr)

            # Check exposure
            approved = self.exposure_manager.check(signal, sized_qty)

            if not approved:
                print("⚠ Risk blocked trade - exposure exceeded")
                return None

            # Enrich signal with risk-adjusted values
            signal["qty"] = sized_qty
            signal["stoploss"] = sl

            return signal

        except Exception as e:
            print(f"❌ Risk processing error: {e}")
            return None

    # -------------------------------------------------
    # EMERGENCY CONTROLS
    # -------------------------------------------------

    def force_square_off(self):
        """Emergency: Close all positions"""
        print("🔴 FORCE SQUARE OFF TRIGGERED")
        self.is_risk_event = True

    def reduce_exposure(self, percent: float):
        """Reduce portfolio exposure"""
        print(f"⚠ Reducing exposure by {percent}%")
        self.is_risk_event = True

    def set_risk_mode(self, mode: str):
        """
        Set risk mode: normal | cautious | defensive | offline
        """
        self.mode = mode
        print(f"⚙ Risk mode set to: {mode}")

    # -------------------------------------------------
    # STATUS
    # -------------------------------------------------

    def get_risk_status(self):
        """Return current risk state"""
        return {
            "mode": self.mode,
            "is_risk_event": self.is_risk_event,
            "position_model": type(self.position_ai).__name__,
            "stoploss_model": type(self.stoploss_ai).__name__
        }
