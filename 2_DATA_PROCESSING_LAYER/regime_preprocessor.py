import logging
from datetime import datetime

logger = logging.getLogger("REGIME_ENGINE")


class RegimePreprocessor:

    def __init__(self):
        # symbol → regime snapshot
        self.regime_state = {}

    # -------------------------------------------------
    # MAIN ENGINE
    # -------------------------------------------------
    def detect_regime(
        self,
        symbol,
        indicator_snapshot,
        feature_vector=None,
        deriv_metrics=None,
        depth_signal=None
    ):
        """
        indicator_snapshot : from technical_indicators
        feature_vector     : from feature_engineering
        deriv_metrics      : from derivatives_metrics_engine
        depth_signal       : from market_depth_collector
        """

        try:
            if not indicator_snapshot:
                return None

            trend_strength = indicator_snapshot.get("trend_strength", 0)
            rsi = indicator_snapshot.get("rsi", 50)
            atr = indicator_snapshot.get("atr", 0)

            volatility_flag = "NORMAL"
            if feature_vector:
                vol = feature_vector.get("volatility", 0)
                if vol > 0.01:
                    volatility_flag = "HIGH_VOL"
                elif vol < 0.003:
                    volatility_flag = "LOW_VOL"

            oi_bias = None
            if deriv_metrics:
                pcr = deriv_metrics.get("pcr_oi")
                if pcr:
                    if pcr > 1.3:
                        oi_bias = "BULLISH"
                    elif pcr < 0.7:
                        oi_bias = "BEARISH"
                    else:
                        oi_bias = "BALANCED"

            liquidity_state = depth_signal or "UNKNOWN"

            # -------- regime decision logic ----------
            regime = "RANGE"

            if abs(trend_strength) > 0.002:
                regime = "TRENDING"

            if volatility_flag == "HIGH_VOL":
                regime = "BREAKOUT"

            if volatility_flag == "LOW_VOL" and abs(trend_strength) < 0.001:
                regime = "MEAN_REVERT"

            snapshot = {
                "symbol": symbol,
                "regime": regime,
                "trend_strength": trend_strength,
                "rsi": rsi,
                "atr": atr,
                "volatility_flag": volatility_flag,
                "oi_bias": oi_bias,
                "liquidity_state": liquidity_state,
                "timestamp": datetime.now()
            }

            self.regime_state[symbol] = snapshot
            return snapshot

        except Exception as e:
            logger.error(f"Regime Detection Error: {e}")
            return None

    # -------------------------------------------------
    # FETCH
    # -------------------------------------------------
    def get_regime(self, symbol):
        return self.regime_state.get(symbol)