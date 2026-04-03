from flask import Flask, jsonify
from datetime import datetime, timezone
import yaml
import threading
import sys
import os


def _configure_console_encoding():
    """Avoid Windows cp1252 crashes from emoji-heavy console logging."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if not hasattr(stream, "reconfigure"):
            continue

        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_console_encoding()

# Add parent directories to Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '1_MARKET_DATA_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '2_DATA_PROCESSING_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '3_STRATEGY_INTELLIGENCE_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '4_AI_DECISION_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '5_RISK_PORTFOLIO_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '6_EXECUTION_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '7_LEARNING_FEEDBACK_LAYER'))

# ---- Market Data Layer ----
from zerodha_socket_feed import ZerodhaSocketFeed  # type: ignore
from fyers_socket_feed import FyersSocketFeed  # type: ignore (fallback)
from derivatives_metrics_engine import DerivativesMetricsEngine  # type: ignore
from market_depth_collector import MarketDepthCollector  # type: ignore
from greeks_calculator import ZerodhaGreeksIntegration, get_greeks_integration  # type: ignore

# ---- Data Processing Layer ----
from technical_indicators import TechnicalIndicators  # type: ignore
from regime_preprocessor import RegimePreprocessor  # type: ignore
from strategy_data_aggregator import StrategyDataAggregator  # type: ignore

# ---- Strategy Layer ----
from trend_strategy import TrendStrategy  # type: ignore
from breakout_strategy import BreakoutStrategy  # type: ignore
from momentum_scalper import MomentumScalper  # type: ignore
from range_decay_strategy import RangeDecayStrategy  # type: ignore
from option_writing_engine import OptionWritingEngine  # type: ignore
from volatility_expansion_strategy import VolatilityExpansionStrategy  # type: ignore

# ---- Execution Layer ----
from order_router import OrderRouter  # type: ignore
from trade_logger import TradeLogger  # type: ignore

# ---- Risk Layer ----
from risk_runtime_engine import RiskRuntimeEngine  # type: ignore
from position_sizing_ai import PositionSizingAI  # type: ignore
from stoploss_optimizer import StoplossOptimizer  # type: ignore
from exposure_manager import ExposureManager  # type: ignore
from sebi_ip_compliance import SEBIIPCompliance, get_ip_compliance  # type: ignore

# ---- Backend Services ----
from websocket_stream import start_websocket_background
from signal_broadcast_service import SignalBroadcastService
from strategy_control_api import StrategyControlAPI
from risk_override_api import RiskOverrideAPI
from data_query_routes import DataQueryRoutes
from notification_service import NotificationService
from performance_analyzer import PerformanceAnalyzer  # type: ignore
from retraining_scheduler import RetrainingScheduler  # type: ignore
from reinforcement_agent import ReinforcementAgent  # type: ignore
from learning_metrics_dashboard_api import LearningMetricsAPI  # type: ignore
from unified_signal_engine import UnifiedSignalEngine, get_unified_engine  # type: ignore
from telegram_alert_service import TelegramAlertService, get_telegram_service, init_telegram  # type: ignore
from order_placement_api import OrderPlacementAPI

# ---- Backend APIs (future integrations) ----
# from strategy_control_api import StrategyControlAPI
# from risk_override_api import RiskOverrideAPI
# from data_query_routes import DataQueryRoutes


class AppServer:

    def __init__(self):

        self.config = self._load_config()
        self.cloud_config = self._load_yaml_file("0_INFRASTRUCTURE_CORE/cloud_config.yaml")

        self.app = Flask(__name__)
        self._configure_cors()

        print("🚀 Initialising AI Options Trading Backend")

        # ===== CORE ENGINES INITIALISATION =====
        self.performance_engine = PerformanceAnalyzer()

        self.rl_agent = ReinforcementAgent(
            self.config.get("rl_config", {})
        )

        self.retraining_engine = RetrainingScheduler(
            self.config.get("retraining", {})
        )

        # ===== START WEBSOCKET ENGINE =====
        self.websocket_engine = start_websocket_background(
            demo_mode=self.config.get("demo_mode", False),
            candle_timeframe_seconds=self.config.get("candle_timeframe_seconds", 60),
            timezone=self._get_market_timezone(),
            market_session=self._get_market_session()
        )
        self.websocket_engine.update_system_status({
            "status": "RUNNING",
            "backend": "RUNNING",
            "mode": self.config.get("trading_mode", "paper"),
            "trading_mode": self.config.get("trading_mode", "paper"),
            "risk_mode": self.config.get("risk_mode", "normal"),
            "broker": self.config.get("broker", "zerodha"),
            "data_mode": "demo" if self.config.get("demo_mode", False) else "live",
            "feed_status": "demo_fallback" if self.config.get("demo_mode", False) else "starting",
            "feed_connected": False,
            "token_state": "not_required" if self.config.get("demo_mode", False) else "checking",
            "demo_fallback": bool(self.config.get("demo_mode", False)),
            "last_tick_time": "",
            "last_error": ""
        })

        # ===== BROADCAST SERVICE =====
        self.broadcast_service = SignalBroadcastService(
            self.websocket_engine
        )

        # ===== NOTIFICATION SERVICE =====
        self.notification_service = NotificationService()

        # ===== TELEGRAM ALERT SERVICE =====
        self.telegram_service = self._init_telegram()

        # ===== TRADE LOGGER =====
        self.trade_logger = TradeLogger(config=self.config)

        # ===== RISK ENGINE INITIALISATION =====
        self.risk_engine = RiskRuntimeEngine(
            position_ai=PositionSizingAI(config=self.config.get("risk_limits", {})),
            stoploss_ai=StoplossOptimizer(config=self.config.get("risk_limits", {})),
            exposure_manager=ExposureManager(config=self.config.get("risk_limits", {}))
        )

        # ===== SEBI IP COMPLIANCE =====
        self.ip_compliance = get_ip_compliance(self.config)
        self.ip_compliance.set_callbacks(
            on_ip_change=self._on_ip_change,
            on_ip_mismatch=self._on_ip_mismatch
        )

        # ===== FEATURE STORE =====
        self.feature_store = None

        # ===== STRATEGY INITIALISATION =====
        self.trend_strategy = TrendStrategy(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        self.breakout_strategy = BreakoutStrategy(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        self.scalper_strategy = MomentumScalper(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        self.range_strategy = RangeDecayStrategy(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        self.option_writer = OptionWritingEngine(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        self.vol_expansion = VolatilityExpansionStrategy(
            config=self.config,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        # ===== STRATEGY REGISTRY =====
        self.strategy_registry = {
            "trend": self.trend_strategy,
            "breakout": self.breakout_strategy,
            "scalper": self.scalper_strategy,
            "range_decay": self.range_strategy,
            "option_writer": self.option_writer,
            "vol_expansion": self.vol_expansion
        }
        
        # ===== AUTO-START ENABLED STRATEGIES =====
        strategies_config = self.config.get("strategies", {})
        for name, strategy in self.strategy_registry.items():
            if strategies_config.get(name, {}).get("enabled", True):
                strategy.start()
                print(f"✅ Auto-started strategy: {name}")

        # ===== DATA PROCESSING LAYER =====
        print("📊 Initializing Data Processing Layer...")
        
        # Technical Indicators Calculator
        self.technical_indicators = TechnicalIndicators()
        
        # Market Depth Collector (will be attached to feed later)
        self.depth_collector = MarketDepthCollector()
        
        # Regime Preprocessor
        self.regime_preprocessor = RegimePreprocessor()
        
        # Derivatives Metrics Engine (needs option chain fetcher from market feed)
        self.derivatives_engine = None  # Will be initialized after market feed
        
        # Strategy Data Aggregator - wires indicators to strategies
        self.data_aggregator = StrategyDataAggregator(
            technical_indicators=self.technical_indicators,
            derivatives_engine=None,  # Will be attached later
            regime_preprocessor=self.regime_preprocessor,
            depth_collector=self.depth_collector,
            strategies=list(self.strategy_registry.values())
        )
        
        print("✅ Data Processing Layer Ready")

        # ===== MARKET DATA FEED =====
        broker = self.config.get("broker", "zerodha").lower()
        
        if broker == "zerodha":
            self.market_feed = ZerodhaSocketFeed(
                api_key=self.config.get("zerodha_api_key", "your_api_key"),
                access_token=self.config.get("zerodha_access_token", "your_access_token"),
                symbols=self.config.get("symbols", ["BANKNIFTY"]),
                exchanges=self.config.get("zerodha_exchanges", ["NSE"]),
                tick_callback=self.websocket_engine.update_market_tick,
                strategies=list(self.strategy_registry.values()),
                status_callback=self.websocket_engine.update_system_status
            )
            print("🟦 Using Zerodha KiteConnect")
        else:
            self.market_feed = FyersSocketFeed(
                access_token=self.config.get("fyers_token", ""),
                symbols=self.config.get("symbols", ["BANKNIFTY"]),
                tick_callback=self.websocket_engine.update_market_tick,
                strategies=list(self.strategy_registry.values())
            )
            print("🟨 Using Fyers (Fallback)")

        # Start market feed in background thread
        feed_thread = threading.Thread(
            target=self.market_feed.start,
            daemon=True
        )
        feed_thread.start()
        print("📡 Market Data Feed Started")

        # ===== WIRE UP DATA AGGREGATOR =====
        # Initialize derivatives engine with option chain fetcher from market feed
        if hasattr(self.market_feed, 'option_chain_fetcher'):
            self.derivatives_engine = DerivativesMetricsEngine(
                self.market_feed.option_chain_fetcher
            )
            self.data_aggregator.derivatives = self.derivatives_engine
            print("📈 Derivatives Engine Connected")
        
        # Attach data aggregator callbacks to market feed for enriched data flow
        if hasattr(self.market_feed, 'candle_engine'):
            # Wire candle updates to aggregator
            original_candle_callback = getattr(self.market_feed.candle_engine, 'on_new_candle', None)
            
            def enriched_candle_callback(symbol, candles):
                # First call aggregator to compute indicators and push to strategies
                self.data_aggregator.on_new_candle(symbol, candles)
                self._push_live_analytics(symbol)
                # Then call original callback if it exists
                if original_candle_callback:
                    original_candle_callback(symbol, candles)
            
            if hasattr(self.market_feed.candle_engine, 'set_candle_callback'):
                self.market_feed.candle_engine.set_candle_callback(enriched_candle_callback)
            print("📊 Candle Data Aggregation Enabled")
        
        # Attach tick enrichment to feed
        original_tick_callback = self.market_feed.tick_callback
        
        def enriched_tick_callback(tick_data):
            # Enrich tick with indicators and push to strategies
            self.data_aggregator.on_tick(tick_data)
            # Call original callback for websocket streaming
            if original_tick_callback:
                original_tick_callback(tick_data)
        
        self.market_feed.tick_callback = enriched_tick_callback
        print("🔄 Tick Data Enrichment Enabled")

        # ===== GREEKS INTEGRATION =====
        self.greeks_integration = get_greeks_integration(self.market_feed)
        self.websocket_engine.attach_greeks_integration(self.greeks_integration)
        
        # Start Greeks polling thread
        self._start_greeks_polling()
        print("📊 Real-time Greeks Integration Enabled")

        # ===== EXECUTION ENGINE =====
        self.order_router = OrderRouter(
            broker_session_path="6_EXECUTION_LAYER/broker_auth_session.json",
            trade_logger=self.trade_logger,
            broadcast_service=self.broadcast_service,
            notification_service=self.notification_service
        )

        # Attach execution engine to broadcast service
        self.broadcast_service.attach_execution_engine(
            self.order_router
        )

        # Attach risk engine to broadcast service
        self.broadcast_service.attach_risk_engine(
            self.risk_engine
        )

        # Attach trade logger to performance engine
        self.performance_engine.attach_trade_logger(
            self.trade_logger
        )
        
        # Attach performance analyzer to WebSocket for accurate accuracy tracking
        self.websocket_engine.attach_performance_analyzer(self.performance_engine)

        # ===== UNIFIED SIGNAL ENGINE =====
        self.unified_engine = get_unified_engine(self.config)
        self.websocket_engine.attach_unified_engine(self.unified_engine)
        print("🧠 Unified AI Signal Engine Attached")

        # ===== API MODULE =====
        self.learning_api = LearningMetricsAPI(
            self.performance_engine,
            self.retraining_engine,
            self.rl_agent
        )

        self._register_routes()

    def _configure_cors(self):
        if not self.config.get("api", {}).get("cors_enabled", False):
            return

        @self.app.after_request
        def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            return response

    # ------------------------------------------------

    def _load_config(self):
        """Load config from backend_settings.yaml with multiple path fallbacks."""
        import os
        
        # Try multiple paths for flexibility
        possible_paths = [
            "backend_settings.yaml",  # Same directory (when run from 8_BACKEND_APPLICATION_LAYER)
            "8_BACKEND_APPLICATION_LAYER/backend_settings.yaml",  # From repo root
            os.path.join(os.path.dirname(__file__), "backend_settings.yaml"),  # Absolute path
        ]
        
        for path in possible_paths:
            try:
                config = self._load_yaml_file(path)
                if config:
                    print(f"✓ Loaded config from: {path}")
                    # Force demo_mode to False for live trading
                    if config.get("demo_mode") is None:
                        config["demo_mode"] = False
                    return config
            except Exception:
                continue
        
        print("⚠ Backend config load failed from all paths, using default")
        return self._get_default_config()

    def _load_yaml_file(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
                return loaded if loaded else {}
        except Exception:
            return {}

    def _get_market_timezone(self):
        system_config = self.cloud_config.get("system", {})
        return system_config.get("timezone", "Asia/Kolkata")

    def _get_market_session(self):
        trading_session = self.cloud_config.get("trading_session", {})
        return {
            "pre_open_start": trading_session.get("pre_open_start", "09:00"),
            "market_start": trading_session.get("market_start", "09:15"),
            "market_close": trading_session.get("market_close", "15:30")
        }

    def _on_ip_change(self, old_ip: str, new_ip: str):
        """Handle IP address change - send notification."""
        msg = f"🔄 IP Changed: {old_ip} → {new_ip}"
        print(msg)
        if self.notification_service:
            self.notification_service.send_alert(
                level="warning",
                title="IP Address Changed",
                message=msg
            )
        # Send Telegram alert
        if self.telegram_service:
            self.telegram_service.send_ip_change_alert(old_ip, new_ip)
        # Update WebSocket status
        if self.websocket_engine:
            self.websocket_engine.update_system_status({
                "ip_address": new_ip,
                "ip_changed": True
            })

    def _on_ip_mismatch(self, current_ip: str, registered_ips: list):
        """Handle IP mismatch - block orders and alert."""
        msg = f"🚨 IP MISMATCH: {current_ip} not in registered IPs. Orders will be rejected by SEBI rules!"
        print(msg)
        if self.notification_service:
            self.notification_service.send_alert(
                level="critical",
                title="SEBI IP Compliance Alert",
                message=f"Current IP {current_ip} is not registered. Orders blocked!"
            )
        # Send Telegram alert
        if self.telegram_service:
            self.telegram_service.send_risk_alert(
                "critical",
                "SEBI IP Compliance",
                f"Current IP {current_ip} not registered!\nOrders BLOCKED."
            )
        # Update WebSocket with warning
        if self.websocket_engine:
            self.websocket_engine.update_system_status({
                "ip_address": current_ip,
                "ip_match": False,
                "ip_warning": "Orders blocked - IP not registered with SEBI"
            })

    def _init_telegram(self):
        """Initialize Telegram alert service."""
        telegram_config = self.config.get("telegram", {})
        
        if not telegram_config.get("enabled", False):
            print("📱 Telegram Alerts: Disabled")
            return None
        
        bot_token = telegram_config.get("bot_token", "")
        chat_id = telegram_config.get("chat_id", "")
        
        if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
            print("📱 Telegram: Not configured (set bot_token in backend_settings.yaml)")
            return None
        
        if not chat_id or chat_id == "YOUR_CHAT_ID_HERE":
            print("📱 Telegram: Not configured (set chat_id in backend_settings.yaml)")
            return None
        
        service = init_telegram(bot_token, chat_id, enabled=True)
        
        # Test connection
        if service.test_connection():
            print("✅ Telegram Alerts: Connected and Active")
            # Attach to broadcast service for signal forwarding
            self._attach_telegram_to_broadcasts(service)
        else:
            print("❌ Telegram Alerts: Connection failed")
        
        return service

    def _attach_telegram_to_broadcasts(self, telegram_service):
        """Attach Telegram to receive all signal broadcasts."""
        telegram_config = self.config.get("telegram", {})
        min_confidence = telegram_config.get("min_confidence", 60)
        
        # Subscribe to notifications
        def on_notification(notification):
            try:
                notif_type = notification.get("type", "")
                
                if notif_type == "STRATEGY_SIGNAL" and telegram_config.get("send_signals", True):
                    confidence = notification.get("confidence", 0)
                    if confidence >= min_confidence:
                        telegram_service.send_signal(notification)
                
                elif notif_type == "TRADE_EXECUTED" and telegram_config.get("send_executions", True):
                    telegram_service.send_trade_execution(notification)
                
                elif notif_type == "RISK_EVENT" and telegram_config.get("send_risk_alerts", True):
                    telegram_service.send_risk_alert(
                        notification.get("severity", "info"),
                        notification.get("event_type", "Risk Event"),
                        notification.get("message", "")
                    )
                
                elif notif_type == "SYSTEM_ALERT" and telegram_config.get("send_risk_alerts", True):
                    telegram_service.send_risk_alert(
                        notification.get("level", "info"),
                        notification.get("title", "Alert"),
                        notification.get("message", "")
                    )
                    
            except Exception as e:
                print(f"Telegram notification error: {e}")
        
        self.notification_service.subscribe(on_notification)

    def _start_greeks_polling(self):
        """Start background thread to poll Greeks from option chain."""
        import time
        
        def poll_greeks():
            while True:
                try:
                    # Get spot price for BANKNIFTY
                    spot_price = None
                    if hasattr(self.market_feed, 'get_spot_price'):
                        spot_price = self.market_feed.get_spot_price("BANKNIFTY")
                    
                    # Calculate Greeks for main symbols
                    for symbol in ["BANKNIFTY", "NIFTY"]:
                        try:
                            greeks_data = self.greeks_integration.calculate_chain_greeks(
                                symbol, 
                                spot_price if symbol == "BANKNIFTY" else None
                            )
                            
                            if greeks_data and greeks_data.get("delta") is not None:
                                # Update WebSocket with real Greeks
                                self.websocket_engine.update_greeks({
                                    "delta": greeks_data.get("delta", 0),
                                    "gamma": greeks_data.get("gamma", 0),
                                    "theta": greeks_data.get("theta", 0),
                                    "vega": greeks_data.get("vega", 0),
                                    "iv": greeks_data.get("atm_iv", 20),
                                    "iv_percentile": greeks_data.get("iv_percentile", 50),
                                    "pcr_oi": greeks_data.get("pcr_oi", 1.0),
                                    "dte": greeks_data.get("dte", 7),
                                    "symbol": symbol
                                })
                                
                                # Also update unified engine
                                if self.unified_engine:
                                    self.unified_engine.update_greeks(greeks_data)
                                
                                print(f"📊 Greeks updated for {symbol}: Δ={greeks_data.get('delta', 0):.3f} IV={greeks_data.get('atm_iv', 20):.1f}%")
                                break  # Only need one successful update
                                
                        except Exception as e:
                            print(f"⚠️ Greeks fetch error for {symbol}: {e}")
                            continue
                    
                except Exception as e:
                    print(f"⚠️ Greeks polling error: {e}")
                
                # Poll every 30 seconds during market hours
                time.sleep(30)
        
        greeks_thread = threading.Thread(target=poll_greeks, daemon=True)
        greeks_thread.start()
        print("📊 Greeks Polling Thread Started")

    def _format_regime_label(self, value):
        text = str(value or "Neutral").strip()
        if not text:
            return "Neutral"
        return text.replace("_", " ").title()

    def _build_live_analytics(self, symbol):
        normalized_symbol = str(symbol or "NIFTY").strip().upper()
        indicators = self.technical_indicators.get_latest(normalized_symbol) or {}
        regime_snapshot = self.regime_preprocessor.get_regime(normalized_symbol) or {}
        deriv_metrics = self.derivatives_engine.get_metrics(normalized_symbol) if self.derivatives_engine else {}
        live_greeks = {}

        if self.websocket_engine and hasattr(self.websocket_engine, "greeks_by_symbol"):
            live_greeks = self.websocket_engine.greeks_by_symbol.get(normalized_symbol, {}) or {}

        regime = (
            deriv_metrics.get("market_regime")
            or regime_snapshot.get("regime")
            or "Neutral"
        )

        volatility = deriv_metrics.get("atm_iv")
        if volatility is None:
            volatility = live_greeks.get("iv")
        if volatility is None:
            atr = indicators.get("atr")
            last_price = indicators.get("last_price") or indicators.get("ltp")
            if atr and last_price:
                volatility = (atr / last_price) * 100
            else:
                volatility = 0

        rsi = indicators.get("rsi")
        momentum_slope = indicators.get("momentum_slope")
        if isinstance(rsi, (int, float)):
            momentum = max(-100.0, min(100.0, (float(rsi) - 50.0) * 2.0))
        elif isinstance(momentum_slope, (int, float)):
            momentum = max(-100.0, min(100.0, float(momentum_slope) * 10000.0))
        else:
            momentum = 0.0

        return {
            "symbol": normalized_symbol,
            "regime": self._format_regime_label(regime),
            "volatility": round(max(0.0, min(100.0, float(volatility))), 1),
            "momentum": round(momentum, 1),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def _push_live_analytics(self, symbol):
        if not self.websocket_engine:
            return

        analytics = self._build_live_analytics(symbol)
        self.websocket_engine.update_analytics(analytics)

    def _start_greeks_polling(self):
        """Start background thread to poll Greeks and derivatives analytics."""
        import time

        def poll_greeks():
            while True:
                try:
                    active_symbol = getattr(self.websocket_engine, "active_symbol", "NIFTY")
                    configured_symbols = self.config.get("symbols", []) or []
                    feed_symbols = getattr(self.market_feed, "symbols", []) or []

                    symbols_to_poll = []
                    for candidate in [active_symbol, *feed_symbols, *configured_symbols]:
                        normalized = str(candidate or "").strip().upper()
                        if normalized and normalized not in symbols_to_poll:
                            symbols_to_poll.append(normalized)

                    for symbol in symbols_to_poll:
                        try:
                            spot_price = None
                            if self.websocket_engine:
                                live_tick = self.websocket_engine.latest_market_tick.get(symbol, {})
                                spot_price = live_tick.get("price") or live_tick.get("ltp")

                            if spot_price is None and hasattr(self.market_feed, "get_spot_price"):
                                spot_price = self.market_feed.get_spot_price(symbol)

                            if self.derivatives_engine and spot_price:
                                self.data_aggregator.on_option_chain_update(symbol, spot_price)
                                self._push_live_analytics(symbol)

                            greeks_data = self.greeks_integration.calculate_chain_greeks(symbol, spot_price)

                            if greeks_data and greeks_data.get("delta") is not None:
                                self.websocket_engine.update_greeks({
                                    "delta": greeks_data.get("delta", 0),
                                    "gamma": greeks_data.get("gamma", 0),
                                    "theta": greeks_data.get("theta", 0),
                                    "vega": greeks_data.get("vega", 0),
                                    "iv": greeks_data.get("atm_iv", 20),
                                    "iv_percentile": greeks_data.get("iv_percentile", 50),
                                    "pcr_oi": greeks_data.get("pcr_oi", 1.0),
                                    "dte": greeks_data.get("dte", 7),
                                    "symbol": symbol
                                })

                                if self.unified_engine:
                                    self.unified_engine.update_greeks(greeks_data)

                                self._push_live_analytics(symbol)
                                print(f"Greeks updated for {symbol}: delta={greeks_data.get('delta', 0):.3f} IV={greeks_data.get('atm_iv', 20):.1f}%")

                        except Exception as e:
                            print(f"Greeks fetch error for {symbol}: {e}")
                            continue

                except Exception as e:
                    print(f"Greeks polling error: {e}")

                time.sleep(10)

        greeks_thread = threading.Thread(target=poll_greeks, daemon=True)
        greeks_thread.start()
        print("Greeks Polling Thread Started")

    def _get_default_config(self):
        """Return default configuration if no file or empty file"""
        return {
            # ===== ZERODHA (Primary) =====
            "broker": "zerodha",  # Primary broker
            "zerodha_api_key": "your_api_key_here",
            "zerodha_access_token": "your_access_token_here",
            "zerodha_exchanges": ["NSE"],
            
            # ===== FYERS (Fallback) =====
            # NOTE: Set these via environment variables or backend_settings.yaml
            "fyers_app_id": os.environ.get("FYERS_APP_ID", ""),
            "fyers_secret": os.environ.get("FYERS_SECRET", ""),
            "fyers_token": os.environ.get("FYERS_TOKEN", ""),
            
            "symbols": ["BANKNIFTY", "NIFTY", "FINNIFTY"],
            "demo_mode": False,  # Default to live mode
            "candle_timeframe_seconds": 60,
            "trading_mode": "paper",
            "risk_mode": "normal",
            "rl_config": {
                "learning_rate": 0.001,
                "discount_factor": 0.99,
                "exploration_rate": 0.1
            },
            "retraining": {
                "frequency_trades": 100,
                "min_samples": 50
            },
            "strategies": {
                "trend": {"enabled": True},
                "breakout": {"enabled": True},
                "scalper": {"enabled": True},
                "range_decay": {"enabled": True},
                "option_writer": {"enabled": True},
                "vol_expansion": {"enabled": True}
            }
        }

    # ------------------------------------------------

    def _register_routes(self):

        self.app.register_blueprint(
            self.learning_api.get_blueprint()
        )

        # ----- Strategy Control -----
        strategy_api = StrategyControlAPI(
            self.strategy_registry
        )
        self.app.register_blueprint(
            strategy_api.get_blueprint()
        )

        # ----- Risk Override -----
        risk_api = RiskOverrideAPI(
            self.risk_engine
        )
        self.app.register_blueprint(
            risk_api.get_blueprint()
        )

        # ----- Data Query -----
        data_api = DataQueryRoutes(
            self.performance_engine,
            self.trade_logger,
            self.feature_store,
            market_feed=self.market_feed,
            websocket_engine=self.websocket_engine
        )
        self.app.register_blueprint(
            data_api.get_blueprint()
        )

        # ----- Order Placement -----
        order_api = OrderPlacementAPI(
            order_router=self.order_router,
            trade_logger=self.trade_logger,
            market_feed=self.market_feed,
            notification_service=self.notification_service,
            risk_engine=self.risk_engine
        )
        self.app.register_blueprint(
            order_api.get_blueprint()
        )

        @self.app.route("/health")
        def health():
            system_status = dict(self.websocket_engine.system_status or {})
            ip_status = self.ip_compliance.get_status()
            return jsonify({
                "status": "RUNNING",
                "engine": "AI_OPTIONS_TRADER",
                "mode": self.config.get("trading_mode", "paper"),
                "data_mode": system_status.get("data_mode", "unknown"),
                "feed_status": system_status.get("feed_status", "unknown"),
                "market_state": system_status.get("market_state", "unknown"),
                "token_state": system_status.get("token_state", "unknown"),
                "ip_compliance": {
                    "current_ip": ip_status.get("current_ip"),
                    "ip_match": ip_status.get("ip_match"),
                    "can_trade": ip_status.get("can_trade")
                }
            })

        @self.app.route("/api/ip-status")
        def ip_status():
            """Get SEBI IP compliance status."""
            return jsonify(self.ip_compliance.get_status())

        @self.app.route("/api/ip-validate")
        def ip_validate():
            """Validate if current IP can place orders."""
            return jsonify(self.ip_compliance.validate_order_ip())

        @self.app.route("/api/ip-add/<ip_address>", methods=["POST"])
        def ip_add(ip_address):
            """Add a new IP to registered IPs."""
            self.ip_compliance.add_registered_ip(ip_address)
            return jsonify({
                "success": True,
                "message": f"Added IP {ip_address}",
                "registered_ips": self.ip_compliance.registered_ips
            })

        @self.app.route("/api/telegram/status")
        def telegram_status():
            """Get Telegram alert service status."""
            if self.telegram_service:
                return jsonify({
                    "enabled": True,
                    "connected": True,
                    "chat_id": self.config.get("telegram", {}).get("chat_id", "")
                })
            return jsonify({
                "enabled": False,
                "connected": False,
                "message": "Telegram not configured"
            })

        @self.app.route("/api/telegram/test", methods=["POST"])
        def telegram_test():
            """Send a test message to Telegram."""
            if self.telegram_service:
                self.telegram_service.send("🧪 <b>Test Message</b>\n\nTelegram alerts are working!")
                return jsonify({"success": True, "message": "Test message sent"})
            return jsonify({"success": False, "message": "Telegram not configured"})

        @self.app.route("/")
        def root():
            return jsonify({
                "msg": "AI Options Trading Backend Active"
            })

    # ------------------------------------------------

    def run(self):

        api_config = self.config.get("api", {})
        host = api_config.get("host", "0.0.0.0")
        port = api_config.get("port", 8000)

        print(f"✅ Backend Running on {host}:{port}")

        self.app.run(
            host=host,
            port=port,
            debug=api_config.get("debug", False),
            threaded=True
        )


# ------------------------------------------------
# Create module-level app for gunicorn (production WSGI server)
# gunicorn expects: app_server:app
_server_instance = None

def get_server():
    """Get or create the singleton AppServer instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = AppServer()
    return _server_instance

# Expose Flask app at module level for gunicorn
app = get_server().app

if __name__ == "__main__":
    server = get_server()
    server.run()
