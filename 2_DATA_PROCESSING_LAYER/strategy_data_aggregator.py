"""
Strategy Data Aggregator
Combines indicators, regime, and derivatives data into enriched payloads
and pushes them to strategies via on_candle() and on_option_chain() callbacks
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger("STRATEGY_AGGREGATOR")


class StrategyDataAggregator:
    """
    Aggregates data from multiple sources and distributes to strategies.
    
    Data Flow:
    1. TechnicalIndicators → on_candle() with indicator snapshot
    2. DerivativesMetricsEngine → on_option_chain() with derivatives data
    3. RegimePreprocessor → Combined into both payloads
    4. MarketDepthCollector → Orderflow data added to tick/candle
    """

    def __init__(
        self,
        technical_indicators,
        derivatives_engine,
        regime_preprocessor,
        depth_collector,
        strategies: List[Any]
    ):
        self.indicators = technical_indicators
        self.derivatives = derivatives_engine
        self.regime = regime_preprocessor
        self.depth = depth_collector
        self.strategies = strategies
        
        # Track last update times to avoid duplicate pushes
        self.last_candle_push = {}
        self.last_option_push = {}

    def on_new_candle(self, symbol: str, candles: List[Dict]) -> None:
        """
        Called when a new candle is formed.
        Computes indicators and pushes enriched data to all strategies.
        """
        try:
            # Compute technical indicators
            indicator_snapshot = self.indicators.compute(symbol, candles)
            
            if indicator_snapshot is None:
                return
            
            # Compute regime based on new indicators
            depth_signal = None
            if hasattr(self.depth, 'get_liquidity_signal'):
                depth_signal = self.depth.get_liquidity_signal(symbol)
            
            regime_data = self.regime.detect_regime(
                symbol, 
                indicator_snapshot,
                depth_signal=depth_signal
            ) or {}
            
            # Get depth data
            depth_data = {}
            if hasattr(self.depth, 'get_latest_depth'):
                latest_depth = self.depth.get_latest_depth(symbol)
                if latest_depth:
                    depth_data = {
                        "imbalance": latest_depth.get("imbalance", 1.0),
                        "spread": latest_depth.get("spread", 0),
                        "signal": depth_signal or "BALANCED"
                    }
            
            # Build enriched candle payload
            enriched_payload = self._build_candle_payload(
                symbol, indicator_snapshot, regime_data, depth_data
            )
            
            # Push to all strategies
            for strategy in self.strategies:
                try:
                    if hasattr(strategy, 'on_candle'):
                        strategy.on_candle(enriched_payload)
                except Exception as e:
                    logger.error(f"Strategy {strategy.name} candle error: {e}")
            
            self.last_candle_push[symbol] = datetime.now()
            
        except Exception as e:
            logger.error(f"Candle aggregation error for {symbol}: {e}")

    def on_option_chain_update(self, symbol: str, spot_price: float) -> None:
        """
        Called when option chain data is refreshed.
        Computes derivatives metrics and pushes to strategies.
        """
        try:
            # Build derivatives metrics
            deriv_metrics = self.derivatives.build_metrics(symbol, spot_price)
            
            if deriv_metrics is None:
                return
            
            # Get current regime
            regime_data = self.regime.get_regime(symbol) if hasattr(self.regime, 'get_regime') else {}
            
            # Build enriched option chain payload
            enriched_payload = self._build_option_payload(
                symbol, spot_price, deriv_metrics, regime_data
            )
            
            # Push to all strategies
            for strategy in self.strategies:
                try:
                    if hasattr(strategy, 'on_option_chain'):
                        strategy.on_option_chain(enriched_payload)
                except Exception as e:
                    logger.error(f"Strategy {strategy.name} option chain error: {e}")
            
            self.last_option_push[symbol] = datetime.now()
            
        except Exception as e:
            logger.error(f"Option chain aggregation error for {symbol}: {e}")

    def on_tick(self, tick_data: Dict) -> None:
        """
        Called on every tick. Enriches tick with latest indicator data.
        """
        symbol = tick_data.get("symbol")
        if not symbol:
            return
        
        try:
            # Get latest indicator snapshot
            indicator_snapshot = self.indicators.get_latest(symbol) or {}
            
            # Get depth data
            depth_data = {}
            if hasattr(self.depth, 'get_latest_depth'):
                latest_depth = self.depth.get_latest_depth(symbol)
                if latest_depth:
                    depth_data = {
                        "imbalance": latest_depth.get("imbalance", 1.0),
                        "spread": latest_depth.get("spread", 0),
                        "signal": self.depth.get_liquidity_signal(symbol) if hasattr(self.depth, 'get_liquidity_signal') else "BALANCED"
                    }
            
            # Enrich tick data
            enriched_tick = {
                **tick_data,
                **indicator_snapshot,
                "orderflow_imbalance": depth_data.get("imbalance", 1.0),
                "spread": depth_data.get("spread", 0),
                "liquidity_signal": depth_data.get("signal", "BALANCED"),
            }
            
            # Push enriched tick to strategies through their market-data router
            # so they can both update state and emit signals from live flow.
            for strategy in self.strategies:
                try:
                    if hasattr(strategy, 'on_market_data'):
                        strategy.on_market_data(enriched_tick)
                    elif hasattr(strategy, 'on_tick'):
                        strategy.on_tick(enriched_tick)
                except Exception as e:
                    logger.error(f"Strategy {strategy.name} tick error: {e}")
                    
        except Exception as e:
            logger.error(f"Tick enrichment error: {e}")

    def _build_candle_payload(
        self,
        symbol: str,
        indicators: Dict,
        regime: Dict,
        depth: Dict
    ) -> Dict:
        """Build enriched candle payload with all required fields for strategies"""
        
        return {
            # Symbol identification
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            
            # Price data (from indicators)
            "ltp": indicators.get("ltp", indicators.get("last_price", 0)),
            "last_price": indicators.get("last_price", indicators.get("ltp", 0)),
            
            # EMAs
            "ema_fast": indicators.get("ema_fast"),
            "ema_mid": indicators.get("ema_mid"),
            "ema_slow": indicators.get("ema_slow"),
            
            # RSI
            "rsi": indicators.get("rsi"),
            "rsi_fast": indicators.get("rsi_fast", indicators.get("rsi")),  # Alias
            
            # ATR and history
            "atr": indicators.get("atr"),
            "prev_atr": indicators.get("prev_atr"),
            
            # VWAP
            "vwap": indicators.get("vwap"),
            
            # Bollinger Bands
            "bb_mid": indicators.get("bb_mid"),
            "bb_upper": indicators.get("bb_upper"),
            "bb_lower": indicators.get("bb_lower"),
            "bb_width": indicators.get("bb_width"),
            "prev_bb_width": indicators.get("prev_bb_width"),
            
            # Trend and momentum
            "trend_strength": indicators.get("trend_strength"),
            "momentum_slope": indicators.get("momentum_slope"),
            "price_velocity": indicators.get("price_velocity"),
            
            # Volume
            "volume_burst": indicators.get("volume_burst", False),
            "volume_spike": indicators.get("volume_burst", False),  # Alias
            
            # Range
            "range_high": indicators.get("range_high"),
            "range_low": indicators.get("range_low"),
            "range_stability_score": indicators.get("range_stability_score"),
            
            # Market regime (multiple key names for compatibility)
            "regime": regime.get("regime", "NEUTRAL"),
            "market_regime": regime.get("regime", "NEUTRAL"),  # Alias for strategies
            "volatility_flag": regime.get("volatility_flag", "NORMAL"),
            
            # Orderflow
            "orderflow_imbalance": depth.get("imbalance", 1.0),
            "spread": depth.get("spread", 0),
            "liquidity_signal": depth.get("signal", "BALANCED"),
            "liquidity_score": self._calculate_liquidity_score(depth),
        }

    def _build_option_payload(
        self,
        symbol: str,
        spot_price: float,
        deriv_metrics: Dict,
        regime: Dict
    ) -> Dict:
        """Build enriched option chain payload"""
        
        return {
            # Symbol identification
            "symbol": symbol,
            "spot_price": spot_price,
            "timestamp": datetime.now().isoformat(),
            
            # ATM info
            "atm_strike": deriv_metrics.get("atm_strike"),
            
            # IV metrics
            "atm_iv": deriv_metrics.get("atm_iv", 20.0),
            "iv_regime": deriv_metrics.get("iv_regime", "NORMAL_VOL"),
            "iv_trend": deriv_metrics.get("iv_trend", "NEUTRAL"),
            "iv_percentile": deriv_metrics.get("iv_percentile", 50.0),
            "iv_change": deriv_metrics.get("iv_change", 0),
            
            # OI metrics
            "pcr_oi": deriv_metrics.get("pcr_oi"),
            "oi_momentum": deriv_metrics.get("oi_momentum", "STABLE"),
            "pressure_zone": deriv_metrics.get("pressure_zone"),
            
            # Theta window
            "theta_window": deriv_metrics.get("theta_window", False),
            
            # Market regime
            "market_regime": deriv_metrics.get("market_regime", regime.get("regime", "NEUTRAL")),
            "regime": deriv_metrics.get("market_regime", regime.get("regime", "NEUTRAL")),
            
            # Regime shift detection for volatility expansion strategy
            "regime_shift": self._detect_regime_shift(symbol, deriv_metrics.get("market_regime")),
        }

    def _calculate_liquidity_score(self, depth: Dict) -> float:
        """Calculate liquidity score from depth data (0-100)"""
        if not depth:
            return 50.0
        
        imbalance = depth.get("imbalance", 1.0)
        spread = depth.get("spread", 0)
        
        # Base score
        score = 50.0
        
        # Balanced imbalance is good
        if 0.7 <= imbalance <= 1.3:
            score += 25
        elif 0.5 <= imbalance <= 1.5:
            score += 10
        
        # Tight spread is good
        if spread < 0.5:
            score += 25
        elif spread < 1.0:
            score += 15
        elif spread < 2.0:
            score += 5
        
        return min(100.0, max(0.0, score))

    def _detect_regime_shift(self, symbol: str, current_regime: str) -> Optional[str]:
        """Detect if regime has shifted (for volatility expansion strategy)"""
        # Store previous regime
        if not hasattr(self, '_prev_regimes'):
            self._prev_regimes = {}
        
        prev_regime = self._prev_regimes.get(symbol)
        self._prev_regimes[symbol] = current_regime
        
        if prev_regime is None:
            return None
        
        # Detect shift to VOL_EXPANSION
        if current_regime == "VOL_EXPANSION" and prev_regime != "VOL_EXPANSION":
            return "VOL_EXPANSION"
        
        # Detect shift to TRENDING
        if current_regime == "TRENDING" and prev_regime not in ["TRENDING", "TRENDING_UP", "TRENDING_DOWN"]:
            return "TRENDING"
        
        return None

    def register_strategy(self, strategy) -> None:
        """Register a new strategy to receive data"""
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            logger.info(f"Registered strategy: {strategy.name}")

    def unregister_strategy(self, strategy) -> None:
        """Unregister a strategy"""
        if strategy in self.strategies:
            self.strategies.remove(strategy)
            logger.info(f"Unregistered strategy: {strategy.name}")
