import logging
import numpy as np
from collections import deque

logger = logging.getLogger("TECH_INDICATORS")


class TechnicalIndicators:

    def __init__(self):
        # symbol → indicator snapshot
        self.indicator_state = {}
        # symbol → history for tracking previous values
        self.indicator_history = {}
        # symbol → price history for velocity calculation
        self.price_history = {}
        # symbol → volume history for burst detection
        self.volume_history = {}

    # -------------------------------------------------
    # MAIN ENGINE
    # -------------------------------------------------
    def compute(self, symbol, candles):

        try:
            if candles is None or len(candles) < 20:
                return None

            closes = np.array([c["close"] for c in candles])
            highs = np.array([c["high"] for c in candles])
            lows = np.array([c["low"] for c in candles])
            volumes = np.array([c.get("volume", 0) for c in candles])

            ema_fast = self._ema(closes, 9)
            ema_mid = self._ema(closes, 21)
            ema_slow = self._ema(closes, 50)

            rsi = self._rsi(closes, 14)
            atr = self._atr(highs, lows, closes, 14)
            vwap = self._vwap(closes, volumes)

            bb_mid, bb_up, bb_low = self._bollinger(closes, 20)

            trend_strength = (ema_fast - ema_slow) / closes[-1]
            
            # NEW: Calculate BB Width
            bb_width = (bb_up - bb_low) / bb_mid if bb_mid > 0 else 0
            
            # NEW: Calculate momentum slope (rate of change)
            momentum_slope = self._momentum_slope(closes, 5)
            
            # NEW: Calculate price velocity
            price_velocity = self._price_velocity(symbol, closes[-1])
            
            # NEW: Calculate volume burst signal
            volume_burst = self._volume_burst(symbol, volumes[-1], volumes)
            
            # NEW: Calculate range high/low (20-period)
            range_high = float(np.max(highs[-20:]))
            range_low = float(np.min(lows[-20:]))
            
            # NEW: Calculate range stability score
            range_stability = self._range_stability(highs[-20:], lows[-20:], closes[-20:])
            
            # Get previous ATR and BB width for expansion detection
            prev_snapshot = self.indicator_state.get(symbol, {})
            prev_atr = prev_snapshot.get("atr", atr)
            prev_bb_width = prev_snapshot.get("bb_width", bb_width)

            snapshot = {
                "symbol": symbol,
                "ema_fast": ema_fast,
                "ema_mid": ema_mid,
                "ema_slow": ema_slow,
                "rsi": rsi,
                "rsi_fast": rsi,  # Alias for momentum scalper
                "atr": atr,
                "prev_atr": prev_atr,
                "vwap": vwap,
                "bb_mid": bb_mid,
                "bb_upper": bb_up,
                "bb_lower": bb_low,
                "bb_width": bb_width,
                "prev_bb_width": prev_bb_width,
                "trend_strength": trend_strength,
                "momentum_slope": momentum_slope,
                "price_velocity": price_velocity,
                "volume_burst": volume_burst,
                "range_high": range_high,
                "range_low": range_low,
                "range_stability_score": range_stability,
                "last_price": float(closes[-1]),
                "ltp": float(closes[-1])
            }

            self.indicator_state[symbol] = snapshot
            return snapshot

        except Exception as e:
            logger.error(f"Indicator Compute Error: {e}")
            return None

    # -------------------------------------------------
    # EMA
    # -------------------------------------------------
    def _ema(self, data, period):
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        ema = np.convolve(data, weights, mode='valid')
        return float(ema[-1])

    # -------------------------------------------------
    # RSI
    # -------------------------------------------------
    def _rsi(self, closes, period):
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    # -------------------------------------------------
    # ATR
    # -------------------------------------------------
    def _atr(self, highs, lows, closes, period):
        trs = []

        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            trs.append(tr)

        return float(np.mean(trs[-period:]))

    # -------------------------------------------------
    # VWAP
    # -------------------------------------------------
    def _vwap(self, closes, volumes):

        vol_sum = np.sum(volumes[-20:])
        if vol_sum == 0:
            return float(closes[-1])

        pv = np.sum(closes[-20:] * volumes[-20:])
        return float(pv / vol_sum)

    # -------------------------------------------------
    # BOLLINGER
    # -------------------------------------------------
    def _bollinger(self, closes, period):

        window = closes[-period:]
        mid = np.mean(window)
        std = np.std(window)

        upper = mid + 2 * std
        lower = mid - 2 * std

        return float(mid), float(upper), float(lower)

    # -------------------------------------------------
    # NEW: MOMENTUM SLOPE
    # -------------------------------------------------
    def _momentum_slope(self, closes, period=5):
        """Calculate rate of price change over period"""
        if len(closes) < period + 1:
            return 0.0
        
        recent = closes[-period:]
        # Linear regression slope normalized by price
        x = np.arange(period)
        slope = np.polyfit(x, recent, 1)[0]
        return float(slope / closes[-1]) if closes[-1] > 0 else 0.0

    # -------------------------------------------------
    # NEW: PRICE VELOCITY
    # -------------------------------------------------
    def _price_velocity(self, symbol, current_price):
        """Calculate price velocity (rate of change)"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=10)
        
        history = self.price_history[symbol]
        history.append(current_price)
        
        if len(history) < 2:
            return 0.0
        
        # Velocity = (current - previous) / previous
        prev_price = history[-2]
        if prev_price == 0:
            return 0.0
        
        return float((current_price - prev_price) / prev_price)

    # -------------------------------------------------
    # NEW: VOLUME BURST DETECTION
    # -------------------------------------------------
    def _volume_burst(self, symbol, current_volume, volumes, threshold=1.5):
        """Detect volume spike relative to moving average"""
        if symbol not in self.volume_history:
            self.volume_history[symbol] = deque(maxlen=20)
        
        history = self.volume_history[symbol]
        history.append(current_volume)
        
        # Calculate average volume
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
        
        if avg_volume == 0:
            return False
        
        # Volume burst if current > threshold * average
        return current_volume > (avg_volume * threshold)

    # -------------------------------------------------
    # NEW: RANGE STABILITY SCORE
    # -------------------------------------------------
    def _range_stability(self, highs, lows, closes):
        """Calculate how stable the price range has been (0-1 scale)"""
        if len(closes) < 5:
            return 0.5
        
        range_width = np.max(highs) - np.min(lows)
        if range_width == 0:
            return 1.0
        
        # Calculate how often price stays within middle 50% of range
        mid_point = (np.max(highs) + np.min(lows)) / 2
        mid_range = range_width * 0.25  # 25% above and below mid
        
        within_mid = np.sum((closes >= mid_point - mid_range) & (closes <= mid_point + mid_range))
        stability = within_mid / len(closes)
        
        return float(stability)

    # -------------------------------------------------
    # FETCH
    # -------------------------------------------------
    def get_latest(self, symbol):
        return self.indicator_state.get(symbol)