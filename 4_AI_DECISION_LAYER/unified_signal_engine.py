"""
Unified AI Signal Engine
========================
Combines all strategy signals with Greeks analysis to produce
ONE clear actionable trade signal.

Features:
- Ensemble voting across all active strategies
- Greeks integration (Delta, Gamma, Theta, Vega)
- Clear BUY/SELL/HOLD decision with confidence
- Exact Entry, Target, Stop-Loss levels
- Signal history for accuracy tracking
"""

from datetime import datetime, timedelta
from collections import deque
import math
import logging

logger = logging.getLogger("UNIFIED_SIGNAL")


class UnifiedSignalEngine:
    """
    Master signal engine that produces ONE unified trade decision
    from multiple strategies and options Greeks.
    """

    def __init__(self, config=None):
        self.config = config or {}
        
        # Strategy weights (higher = more influence)
        self.strategy_weights = {
            "TrendStrategy": 1.5,
            "BreakoutStrategy": 1.3,
            "MomentumScalper": 1.0,
            "RangeDecayStrategy": 0.8,
            "OptionWritingEngine": 1.2,
            "VolatilityExpansionStrategy": 1.4
        }
        
        # Signal collection window
        self.signal_buffer = deque(maxlen=50)
        self.signal_history = deque(maxlen=500)
        
        # Current unified signal
        self.current_signal = None
        self.current_signals = {}
        
        # Greeks data
        self.greeks = {
            "delta": 0,
            "gamma": 0,
            "theta": 0,
            "vega": 0,
            "iv": 20.0,
            "iv_percentile": 50.0
        }
        
        # Performance tracking
        self.signal_stats = {
            "total_signals": 0,
            "buy_signals": 0,
            "sell_signals": 0,
            "correct_predictions": 0,
            "accuracy": 0
        }
        
        # Minimum confidence to emit signal
        self.min_confidence = config.get("min_confidence", 0.55)
        
        # Signal cooldown (seconds between signals)
        self.signal_cooldown = config.get("signal_cooldown", 30)
        self.last_signal_time = None
        self.last_signal_time_by_symbol = {}
        
        print("🧠 Unified Signal Engine Initialized")

    def collect_strategy_signal(self, strategy_name: str, signal: dict):
        """
        Collect signal from a strategy for ensemble processing.
        Called by each strategy when it generates a signal.
        """
        if not signal:
            return
        
        enriched_signal = {
            "strategy": strategy_name,
            "direction": signal.get("direction", "HOLD"),
            "confidence": signal.get("confidence", 0),
            "symbol": signal.get("symbol", "UNKNOWN"),
            "entry_price": signal.get("entry_price", 0),
            "target": signal.get("target", 0),
            "stoploss": signal.get("stoploss", 0),
            "timestamp": datetime.now()
        }
        
        self.signal_buffer.append(enriched_signal)
        logger.info(f"Collected signal from {strategy_name}: {signal.get('direction')}")

    def update_greeks(self, greeks_data: dict):
        """
        Update options Greeks from derivatives engine.
        """
        if not greeks_data:
            return
        
        self.greeks.update({
            "delta": greeks_data.get("delta", self.greeks["delta"]),
            "gamma": greeks_data.get("gamma", self.greeks["gamma"]),
            "theta": greeks_data.get("theta", self.greeks["theta"]),
            "vega": greeks_data.get("vega", self.greeks["vega"]),
            "iv": greeks_data.get("atm_iv", self.greeks["iv"]),
            "iv_percentile": greeks_data.get("iv_percentile", self.greeks["iv_percentile"])
        })

    def compute_unified_signal(self, spot_price: float = None, symbol: str = None) -> dict:
        """
        Compute the unified trading signal from all collected signals
        and Greeks analysis.
        
        Returns:
            dict: Unified signal with action, confidence, entry, target, SL
        """
        signal_symbol = symbol or "BANKNIFTY"

        # Check cooldown per symbol
        last_signal_time = self.last_signal_time_by_symbol.get(signal_symbol)
        if last_signal_time:
            elapsed = (datetime.now() - last_signal_time).total_seconds()
            if elapsed < self.signal_cooldown:
                return self.current_signals.get(signal_symbol) or self.current_signal
        
        # Get recent signals (last 30 seconds)
        cutoff = datetime.now() - timedelta(seconds=30)
        recent_signals = [
            s for s in self.signal_buffer
            if s["timestamp"] > cutoff and s.get("symbol") == signal_symbol
        ]

        if not recent_signals:
            # No strategy signals - use Greeks-only analysis
            return self._greeks_only_signal(spot_price, signal_symbol)
        
        # Ensemble voting
        buy_score = 0
        sell_score = 0
        hold_score = 0
        
        buy_signals = []
        sell_signals = []
        
        for signal in recent_signals:
            strategy = signal["strategy"]
            weight = self.strategy_weights.get(strategy, 1.0)
            confidence = signal.get("confidence", 0)
            
            # Normalize confidence to 0-1 if needed
            if confidence > 1:
                confidence = confidence / 100
            
            weighted_conf = confidence * weight
            
            if signal["direction"] == "BUY":
                buy_score += weighted_conf
                buy_signals.append(signal)
            elif signal["direction"] in ["SELL", "SELL_PREMIUM"]:
                sell_score += weighted_conf
                sell_signals.append(signal)
            else:
                hold_score += weighted_conf
        
        # Apply Greeks adjustments
        greeks_adjustment = self._calculate_greeks_bias()
        buy_score += greeks_adjustment
        sell_score -= greeks_adjustment
        
        # Determine final direction
        max_score = max(buy_score, sell_score, hold_score)

        if max_score < self.min_confidence:
            return self._create_hold_signal(spot_price, max_score, signal_symbol)
        
        # Build unified signal
        if buy_score == max_score and buy_signals:
            signal = self._build_unified_signal(
                direction="BUY",
                signals=buy_signals,
                confidence=buy_score,
                spot_price=spot_price,
                symbol=signal_symbol
            )
        elif sell_score == max_score and sell_signals:
            signal = self._build_unified_signal(
                direction="SELL",
                signals=sell_signals,
                confidence=sell_score,
                spot_price=spot_price,
                symbol=signal_symbol
            )
        else:
            signal = self._create_hold_signal(spot_price, max_score, signal_symbol)

        # Update state
        self.current_signal = signal
        self.current_signals[signal_symbol] = signal
        self.last_signal_time = datetime.now()
        self.last_signal_time_by_symbol[signal_symbol] = self.last_signal_time
        self.signal_history.append(signal)
        self._update_stats(signal)
        
        return signal

    def _calculate_greeks_bias(self) -> float:
        """
        Calculate directional bias from Greeks.
        Positive = bullish, Negative = bearish
        """
        bias = 0.0
        
        # Delta: Positive delta suggests upward pressure
        delta = self.greeks.get("delta", 0)
        if delta > 0.3:
            bias += 0.1
        elif delta < -0.3:
            bias -= 0.1
        
        # Gamma: High gamma = potential for big moves
        gamma = self.greeks.get("gamma", 0)
        # Gamma doesn't give directional bias, but affects conviction
        
        # Theta: Negative theta favors premium selling (bearish on vol)
        theta = self.greeks.get("theta", 0)
        if theta < -50:  # Heavy time decay
            bias -= 0.05  # Slight bearish bias (premium selling)
        
        # Vega: High vega = IV expansion expected
        vega = self.greeks.get("vega", 0)
        iv_percentile = self.greeks.get("iv_percentile", 50)
        
        # High IV percentile + high vega = potential IV crush (bearish vol)
        if iv_percentile > 70 and vega > 100:
            bias -= 0.1  # IV likely to mean revert
        elif iv_percentile < 30 and vega > 100:
            bias += 0.1  # IV likely to expand
        
        return bias

    def _build_unified_signal(self, direction: str, signals: list,
                             confidence: float, spot_price: float, symbol: str = None) -> dict:
        """
        Build the final unified signal from contributing signals.
        """
        # Get best entry, target, SL from contributing signals
        if signals:
            # Weighted average of entry prices
            entries = [s["entry_price"] for s in signals if s["entry_price"]]
            targets = [s["target"] for s in signals if s["target"]]
            stoplosses = [s["stoploss"] for s in signals if s["stoploss"]]
            
            entry_price = sum(entries) / len(entries) if entries else spot_price
            
            if direction == "BUY":
                target = max(targets) if targets else entry_price * 1.02
                stoploss = min(stoplosses) if stoplosses else entry_price * 0.99
            else:
                target = min(targets) if targets else entry_price * 0.98
                stoploss = max(stoplosses) if stoplosses else entry_price * 1.01
            
            # Get contributing strategies
            strategies = list(set(s["strategy"] for s in signals))
            symbol = signals[0].get("symbol", symbol or "BANKNIFTY")
        else:
            entry_price = spot_price or 50000
            target = entry_price * (1.02 if direction == "BUY" else 0.98)
            stoploss = entry_price * (0.99 if direction == "BUY" else 1.01)
            strategies = []
            symbol = symbol or "BANKNIFTY"
        
        # Normalize confidence to percentage
        conf_pct = confidence * 100 if confidence <= 1 else confidence
        
        # Calculate accuracy from history
        accuracy = self._calculate_accuracy()
        
        return {
            "action": direction,
            "symbol": symbol,
            "confidence": round(min(conf_pct, 95), 1),
            "accuracy": round(accuracy, 1),
            "entry_price": round(entry_price, 2),
            "target": round(target, 2),
            "stoploss": round(stoploss, 2),
            "risk_reward": round(abs(target - entry_price) / abs(entry_price - stoploss), 2) if stoploss != entry_price else 0,
            "contributing_strategies": strategies,
            "strategy": strategies[0] if strategies else "UnifiedAI",
            "greeks": {
                "delta": round(self.greeks.get("delta", 0), 3),
                "gamma": round(self.greeks.get("gamma", 0), 4),
                "theta": round(self.greeks.get("theta", 0), 2),
                "vega": round(self.greeks.get("vega", 0), 2),
                "iv": round(self.greeks.get("iv", 20), 1),
                "iv_percentile": round(self.greeks.get("iv_percentile", 50), 1)
            },
            "timestamp": datetime.now().isoformat(),
            "signal_type": "UNIFIED_AI"
        }

    def _create_hold_signal(self, spot_price: float, score: float, symbol: str = "BANKNIFTY") -> dict:
        """Create a HOLD signal when no clear direction."""
        price = spot_price or 50000
        
        return {
            "action": "HOLD",
            "symbol": symbol,
            "confidence": round(score * 100 if score <= 1 else score, 1),
            "accuracy": round(self._calculate_accuracy(), 1),
            "entry_price": round(price, 2),
            "target": round(price, 2),
            "stoploss": round(price, 2),
            "risk_reward": 0,
            "contributing_strategies": [],
            "strategy": "UnifiedAI",
            "greeks": {
                "delta": round(self.greeks.get("delta", 0), 3),
                "gamma": round(self.greeks.get("gamma", 0), 4),
                "theta": round(self.greeks.get("theta", 0), 2),
                "vega": round(self.greeks.get("vega", 0), 2),
                "iv": round(self.greeks.get("iv", 20), 1),
                "iv_percentile": round(self.greeks.get("iv_percentile", 50), 1)
            },
            "timestamp": datetime.now().isoformat(),
            "signal_type": "UNIFIED_AI",
            "reason": "No clear consensus - waiting for stronger signal"
        }

    def _greeks_only_signal(self, spot_price: float, symbol: str = "BANKNIFTY") -> dict:
        """
        Generate signal based purely on Greeks when no strategy signals.
        Useful for options-specific trading decisions.
        """
        price = spot_price or 50000
        
        iv = self.greeks.get("iv", 20)
        iv_percentile = self.greeks.get("iv_percentile", 50)
        theta = self.greeks.get("theta", 0)
        delta = self.greeks.get("delta", 0)
        
        # Determine action based on Greeks
        action = "HOLD"
        confidence = 40
        
        # High IV percentile = good for premium selling
        if iv_percentile > 70 and theta < -30:
            action = "SELL_PREMIUM"
            confidence = 55 + (iv_percentile - 70)
        # Low IV = potential for vol expansion
        elif iv_percentile < 30 and iv < 15:
            action = "BUY"  # Buy options for vol expansion
            confidence = 50 + (30 - iv_percentile)
        # Strong delta bias
        elif abs(delta) > 0.5:
            action = "BUY" if delta > 0 else "SELL"
            confidence = 50 + abs(delta) * 20
        
        return {
            "action": action,
            "symbol": symbol,
            "confidence": round(min(confidence, 85), 1),
            "accuracy": round(self._calculate_accuracy(), 1),
            "entry_price": round(price, 2),
            "target": round(price * (1.015 if action == "BUY" else 0.985), 2),
            "stoploss": round(price * (0.99 if action == "BUY" else 1.01), 2),
            "risk_reward": 1.5,
            "contributing_strategies": ["GreeksAnalysis"],
            "strategy": "GreeksAnalysis",
            "greeks": {
                "delta": round(self.greeks.get("delta", 0), 3),
                "gamma": round(self.greeks.get("gamma", 0), 4),
                "theta": round(self.greeks.get("theta", 0), 2),
                "vega": round(self.greeks.get("vega", 0), 2),
                "iv": round(iv, 1),
                "iv_percentile": round(iv_percentile, 1)
            },
            "timestamp": datetime.now().isoformat(),
            "signal_type": "GREEKS_BASED",
            "reason": f"Based on IV Percentile: {iv_percentile}%, Delta: {delta}"
        }

    def _calculate_accuracy(self) -> float:
        """Calculate historical accuracy of signals."""
        if self.signal_stats["total_signals"] == 0:
            return 65.0  # Default starting accuracy
        
        return (self.signal_stats["correct_predictions"] / 
                self.signal_stats["total_signals"]) * 100

    def _update_stats(self, signal: dict):
        """Update signal statistics."""
        self.signal_stats["total_signals"] += 1
        
        if signal["action"] == "BUY":
            self.signal_stats["buy_signals"] += 1
        elif signal["action"] == "SELL":
            self.signal_stats["sell_signals"] += 1

    def record_outcome(self, signal_id: str, was_correct: bool):
        """
        Record whether a signal was correct for accuracy tracking.
        Called after trade closes to update accuracy.
        """
        if was_correct:
            self.signal_stats["correct_predictions"] += 1
        
        # Recalculate accuracy
        self.signal_stats["accuracy"] = self._calculate_accuracy()

    def get_signal_summary(self) -> dict:
        """Get summary of current signal state for dashboard."""
        signal = self.current_signal or self._create_hold_signal(None, 0)
        
        return {
            "current_signal": signal,
            "stats": self.signal_stats,
            "greeks": self.greeks,
            "active_strategies": list(self.strategy_weights.keys()),
            "last_update": datetime.now().isoformat()
        }


# Singleton instance for global access
_unified_engine = None

def get_unified_engine(config=None) -> UnifiedSignalEngine:
    """Get or create the global unified signal engine."""
    global _unified_engine
    if _unified_engine is None:
        _unified_engine = UnifiedSignalEngine(config)
    return _unified_engine
