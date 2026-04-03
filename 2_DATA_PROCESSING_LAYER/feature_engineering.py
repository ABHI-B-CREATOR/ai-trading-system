import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger("FEATURE_ENGINE")


class FeatureEngineering:

    def __init__(self):
        # symbol → last computed feature vector
        self.feature_state = {}

    # -------------------------------------------------
    # MAIN FEATURE BUILDER
    # -------------------------------------------------
    def build_features(
        self,
        symbol,
        candles,
        deriv_metrics=None,
        depth_signal=None
    ):
        """
        candles : list of candle dicts (latest last)
        deriv_metrics : snapshot from derivatives_metrics_engine
        depth_signal : BUY_PRESSURE / SELL_PRESSURE / BALANCED
        """

        try:
            if not candles or len(candles) < 5:
                return None

            closes = np.array([c["close"] for c in candles])
            highs = np.array([c["high"] for c in candles])
            lows = np.array([c["low"] for c in candles])

            # ---------- price return features ----------
            ret_1 = (closes[-1] - closes[-2]) / closes[-2]
            ret_5 = (closes[-1] - closes[-5]) / closes[-5]

            # ---------- volatility ----------
            ranges = highs - lows
            vol = np.mean(ranges[-5:]) / closes[-1]

            # ---------- momentum slope ----------
            x = np.arange(len(closes[-5:]))
            slope = np.polyfit(x, closes[-5:], 1)[0]

            # ---------- derivatives features ----------
            pcr = None
            iv_regime = 0
            oi_momentum = 0

            if deriv_metrics:
                pcr = deriv_metrics.get("pcr_oi")

                iv_map = {
                    "LOW_VOL": -1,
                    "NORMAL_VOL": 0,
                    "HIGH_VOL": 1
                }
                iv_regime = iv_map.get(deriv_metrics.get("iv_regime"), 0)

                oi_map = {
                    "UNWIND": -1,
                    "STABLE": 0,
                    "BUILDUP": 1
                }
                oi_momentum = oi_map.get(deriv_metrics.get("oi_momentum"), 0)

            # ---------- depth feature ----------
            depth_map = {
                "SELL_PRESSURE": -1,
                "BALANCED": 0,
                "BUY_PRESSURE": 1
            }
            depth_val = depth_map.get(depth_signal, 0)

            feature_vector = {
                "symbol": symbol,
                "ret_1": ret_1,
                "ret_5": ret_5,
                "volatility": vol,
                "momentum_slope": slope,
                "pcr": pcr,
                "iv_regime": iv_regime,
                "oi_momentum": oi_momentum,
                "depth_pressure": depth_val,
                "timestamp": datetime.now()
            }

            self.feature_state[symbol] = feature_vector
            return feature_vector

        except Exception as e:
            logger.error(f"Feature Build Error: {e}")
            return None

    # -------------------------------------------------
    # FETCH
    # -------------------------------------------------
    def get_latest_features(self, symbol):
        return self.feature_state.get(symbol)