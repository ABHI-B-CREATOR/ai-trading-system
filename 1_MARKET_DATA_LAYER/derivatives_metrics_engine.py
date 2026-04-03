import logging
from statistics import mean
from datetime import datetime
from collections import deque

logger = logging.getLogger("DERIV_METRICS")


class DerivativesMetricsEngine:

    def __init__(self, option_chain_fetcher):
        self.chain = option_chain_fetcher

        # symbol → metrics snapshot
        self.metrics_state = {}
        # symbol → IV history for trend and percentile
        self.iv_history = {}
        # Maximum IV history to keep (for percentile calculation)
        self.max_iv_history = 100

    # -------------------------------------------------
    # MAIN PUBLIC ENGINE
    # -------------------------------------------------
    def build_metrics(self, symbol, spot_price):

        try:
            full_chain = self.chain.get_full_chain(symbol)

            if not full_chain:
                return None

            pcr = self.chain.get_pcr_oi(symbol)
            atm = self.chain.get_atm_strike(symbol, spot_price)

            iv_regime = self._detect_iv_regime(full_chain)
            oi_momentum = self._detect_oi_momentum(full_chain)
            pressure = self._detect_strike_pressure(full_chain, atm)
            
            # NEW: Calculate ATM IV
            atm_iv = self._get_atm_iv(full_chain, atm)
            
            # NEW: Track IV history and calculate trend/percentile
            iv_trend = self._calculate_iv_trend(symbol, atm_iv)
            iv_percentile = self._calculate_iv_percentile(symbol, atm_iv)
            
            # NEW: Calculate IV change from previous
            prev_metrics = self.metrics_state.get(symbol, {})
            prev_iv = prev_metrics.get("atm_iv", atm_iv)
            iv_change = (atm_iv - prev_iv) / prev_iv if prev_iv > 0 else 0
            
            # NEW: Calculate theta window (optimal for premium selling)
            theta_window = self._calculate_theta_window(full_chain)

            snapshot = {
                "symbol": symbol,
                "spot": spot_price,
                "atm_strike": atm,
                "pcr_oi": pcr,
                "iv_regime": iv_regime,
                "oi_momentum": oi_momentum,
                "pressure_zone": pressure,
                # NEW fields
                "atm_iv": atm_iv,
                "iv_trend": iv_trend,
                "iv_percentile": iv_percentile,
                "iv_change": iv_change,
                "theta_window": theta_window,
                "market_regime": self._get_market_regime(iv_regime, oi_momentum),
                "timestamp": datetime.now()
            }

            self.metrics_state[symbol] = snapshot
            return snapshot

        except Exception as e:
            logger.error(f"Derivatives Metrics Error: {e}")
            return None

    # -------------------------------------------------
    # IV REGIME
    # -------------------------------------------------
    def _detect_iv_regime(self, chain):

        iv_values = []

        for strike in chain.values():
            for opt in strike.values():
                if opt.get("iv"):
                    iv_values.append(opt["iv"])

        if not iv_values:
            return "NORMAL"

        avg_iv = mean(iv_values)

        if avg_iv > 25:
            return "HIGH_VOL"

        if avg_iv < 12:
            return "LOW_VOL"

        return "NORMAL_VOL"

    # -------------------------------------------------
    # OI MOMENTUM
    # -------------------------------------------------
    def _detect_oi_momentum(self, chain):

        total_change = 0

        for strike in chain.values():
            for opt in strike.values():
                total_change += opt.get("oi_change", 0)

        if total_change > 0:
            return "BUILDUP"

        if total_change < 0:
            return "UNWIND"

        return "STABLE"

    # -------------------------------------------------
    # STRIKE PRESSURE
    # -------------------------------------------------
    def _detect_strike_pressure(self, chain, atm):

        if atm is None:
            return None

        nearby = []

        for strike, data in chain.items():
            if abs(strike - atm) <= 200:
                for opt in data.values():
                    nearby.append(opt.get("oi", 0))

        if not nearby:
            return None

        avg_oi = mean(nearby)

        if avg_oi > 500000:
            return "HEAVY_POSITIONING"

        return "LIGHT_POSITIONING"

    # -------------------------------------------------
    # NEW: GET ATM IV
    # -------------------------------------------------
    def _get_atm_iv(self, chain, atm_strike):
        """Get implied volatility at ATM strike"""
        if atm_strike is None or atm_strike not in chain:
            return 20.0  # Default IV
        
        strike_data = chain.get(atm_strike, {})
        iv_values = []
        
        for opt in strike_data.values():
            if opt.get("iv"):
                iv_values.append(opt["iv"])
        
        return mean(iv_values) if iv_values else 20.0

    # -------------------------------------------------
    # NEW: CALCULATE IV TREND
    # -------------------------------------------------
    def _calculate_iv_trend(self, symbol, current_iv):
        """Determine if IV is rising or falling"""
        if symbol not in self.iv_history:
            self.iv_history[symbol] = deque(maxlen=self.max_iv_history)
        
        history = self.iv_history[symbol]
        history.append(current_iv)
        
        if len(history) < 5:
            return "NEUTRAL"
        
        # Compare current to 5-period average
        recent_avg = mean(list(history)[-5:])
        older_avg = mean(list(history)[-10:-5]) if len(history) >= 10 else recent_avg
        
        diff = recent_avg - older_avg
        
        if diff > 1.0:  # IV increasing by more than 1%
            return "RISING"
        elif diff < -1.0:  # IV decreasing by more than 1%
            return "FALLING"
        else:
            return "NEUTRAL"

    # -------------------------------------------------
    # NEW: CALCULATE IV PERCENTILE
    # -------------------------------------------------
    def _calculate_iv_percentile(self, symbol, current_iv):
        """Calculate IV percentile rank (0-100)"""
        if symbol not in self.iv_history:
            return 50.0  # Default to middle
        
        history = list(self.iv_history[symbol])
        
        if len(history) < 10:
            return 50.0
        
        # Count how many historical values are below current
        below_count = sum(1 for h in history if h < current_iv)
        percentile = (below_count / len(history)) * 100
        
        return round(percentile, 1)

    # -------------------------------------------------
    # NEW: CALCULATE THETA WINDOW
    # -------------------------------------------------
    def _calculate_theta_window(self, chain):
        """Determine if current time is optimal for theta decay capture"""
        # Check expiry from chain data
        now = datetime.now()
        
        # Look for nearest expiry in chain
        nearest_dte = None
        
        for strike_data in chain.values():
            for opt in strike_data.values():
                expiry = opt.get("expiry")
                if expiry:
                    if isinstance(expiry, str):
                        try:
                            expiry = datetime.fromisoformat(expiry)
                        except ValueError as e:
                            logger.debug(f"Invalid expiry format: {expiry}, skipping")
                            continue
                    dte = (expiry - now).days
                    if nearest_dte is None or dte < nearest_dte:
                        nearest_dte = dte
        
        if nearest_dte is None:
            return False
        
        # Theta window: 7-30 DTE is optimal for premium selling
        return 7 <= nearest_dte <= 30

    # -------------------------------------------------
    # NEW: GET MARKET REGIME
    # -------------------------------------------------
    def _get_market_regime(self, iv_regime, oi_momentum):
        """Combine IV regime and OI momentum into market regime"""
        if iv_regime == "HIGH_VOL":
            return "VOL_EXPANSION"
        elif iv_regime == "LOW_VOL" and oi_momentum == "STABLE":
            return "RANGE"
        elif oi_momentum == "BUILDUP":
            return "TRENDING"
        elif oi_momentum == "UNWIND":
            return "MEAN_REVERT"
        else:
            return "NEUTRAL"

    # -------------------------------------------------
    # FAST FETCH
    # -------------------------------------------------
    def get_metrics(self, symbol):
        return self.metrics_state.get(symbol)