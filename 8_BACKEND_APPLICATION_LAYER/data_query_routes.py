from flask import Blueprint, jsonify, request
from datetime import datetime


class DataQueryRoutes:

    def __init__(self,
                 performance_engine=None,
                 trade_logger=None,
                 feature_store=None,
                 market_feed=None,
                 websocket_engine=None):

        """
        performance_engine → performance_analyzer
        trade_logger → execution trade logger
        feature_store → processed feature DB / memory
        """

        self.performance_engine = performance_engine
        self.trade_logger = trade_logger
        self.feature_store = feature_store
        self.market_feed = market_feed
        self.websocket_engine = websocket_engine

        self.blueprint = Blueprint(
            "data_query_routes",
            __name__,
            url_prefix="/api/data"
        )

        self._register_routes()

        print("📊 Data Query Routes Initialised")

    # -------------------------------------------------

    @staticmethod
    def _parse_candle_time(value):
        if isinstance(value, datetime):
            return value

        if not value:
            return None

        text = str(value).strip()
        if not text:
            return None

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _interval_seconds(interval):
        return {
            "minute": 60,
            "3minute": 3 * 60,
            "5minute": 5 * 60,
            "10minute": 10 * 60,
            "15minute": 15 * 60,
            "30minute": 30 * 60,
            "60minute": 60 * 60,
            "day": 24 * 60 * 60
        }.get(interval)

    @classmethod
    def _bucket_time(cls, candle_time, interval):
        if candle_time is None:
            return None

        if interval == "day":
            return candle_time.replace(hour=0, minute=0, second=0, microsecond=0)

        bucket_seconds = cls._interval_seconds(interval)
        if not bucket_seconds:
            return candle_time

        timestamp = int(candle_time.timestamp())
        bucket_start = timestamp - (timestamp % bucket_seconds)

        if candle_time.tzinfo is not None:
            return datetime.fromtimestamp(bucket_start, tz=candle_time.tzinfo)

        return datetime.fromtimestamp(bucket_start)

    @staticmethod
    def _to_number(value, default=0.0):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default

        if number != number:
            return default

        return number

    @classmethod
    def _aggregate_stream_candles(cls, candles, interval, limit):
        if not candles:
            return []

        sorted_candles = sorted(
            candles,
            key=lambda candle: cls._parse_candle_time((candle or {}).get("time")) or datetime.min
        )

        if interval == "minute":
            return sorted_candles[-limit:]

        aggregated = {}
        ordered_keys = []

        for candle in sorted_candles:
            candle_time = cls._parse_candle_time((candle or {}).get("time"))
            if candle_time is None:
                continue

            bucket_time = cls._bucket_time(candle_time, interval)
            if bucket_time is None:
                continue

            key = bucket_time.isoformat()
            open_price = cls._to_number(candle.get("open"), None)
            high_price = cls._to_number(candle.get("high"), None)
            low_price = cls._to_number(candle.get("low"), None)
            close_price = cls._to_number(candle.get("close"), None)

            if None in (open_price, high_price, low_price, close_price):
                continue

            volume = cls._to_number(candle.get("volume"), 0)
            existing = aggregated.get(key)

            if not existing:
                aggregated[key] = {
                    "time": key,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume
                }
                ordered_keys.append(key)
                continue

            existing["high"] = max(existing["high"], high_price)
            existing["low"] = min(existing["low"], low_price)
            existing["close"] = close_price
            existing["volume"] = cls._to_number(existing.get("volume"), 0) + volume

        return [aggregated[key] for key in ordered_keys[-limit:]]

    def _register_routes(self):

        @self.blueprint.route("/pnl_curve", methods=["GET"])
        def pnl_curve():

            if not self.performance_engine:
                return jsonify({"error": "performance engine missing"}), 500

            data = self.performance_engine.get_equity_curve()

            return jsonify({
                "type": "pnl_curve",
                "data": data
            })

        # -------------------------------------------------

        @self.blueprint.route("/trade_history", methods=["GET"])
        def trade_history():

            limit = int(request.args.get("limit", 50))

            if not self.trade_logger:
                return jsonify({"error": "trade logger missing"}), 500

            trades = self.trade_logger.get_recent_trades(limit)

            return jsonify({
                "type": "trade_history",
                "count": len(trades),
                "data": trades
            })

        # -------------------------------------------------

        @self.blueprint.route("/strategy_stats", methods=["GET"])
        def strategy_stats():

            if not self.performance_engine:
                return jsonify({"error": "performance engine missing"}), 500

            stats = self.performance_engine.get_strategy_metrics()

            return jsonify({
                "type": "strategy_stats",
                "data": stats
            })

        # -------------------------------------------------

        @self.blueprint.route("/feature_snapshot", methods=["GET"])
        def feature_snapshot():

            if not self.feature_store:
                return jsonify({"error": "feature store missing"}), 500

            snapshot = self.feature_store.get_latest_features()

            return jsonify({
                "type": "feature_snapshot",
                "time": datetime.utcnow().isoformat(),
                "data": snapshot
            })

        # -------------------------------------------------

        @self.blueprint.route("/system_summary", methods=["GET"])
        def system_summary():

            summary = {
                "time": datetime.utcnow().isoformat(),
                "status": "RUNNING",
                "modules": {
                    "execution": True,
                    "ai_engine": True,
                    "risk_engine": True,
                    "data_pipeline": True
                }
            }

            return jsonify(summary)

        # -------------------------------------------------

        @self.blueprint.route("/chart_history", methods=["GET"])
        def chart_history():

            symbol = request.args.get("symbol", "NIFTY")
            exchange = request.args.get("exchange")
            interval = request.args.get("interval", "day")
            days = int(request.args.get("days", 180))
            limit = int(request.args.get("limit", 300))

            candles = []
            source = "unavailable"
            error = None

            allowed_intervals = {
                "minute",
                "3minute",
                "5minute",
                "10minute",
                "15minute",
                "30minute",
                "60minute",
                "day"
            }

            if interval not in allowed_intervals:
                return jsonify({
                    "error": f"unsupported interval: {interval}"
                }), 400

            if self.market_feed and hasattr(self.market_feed, "get_historical_candles"):
                try:
                    candles = self.market_feed.get_historical_candles(
                        symbol=symbol,
                        exchange=exchange,
                        interval=interval,
                        days=days
                    )
                    if candles:
                        source = "historical_api"
                except Exception as exc:
                    error = str(exc)

            if not candles and self.websocket_engine:
                stream_candles = self.websocket_engine.latest_candles.get(symbol, [])
                candles = self._aggregate_stream_candles(
                    stream_candles,
                    interval=interval,
                    limit=limit
                )
                if candles:
                    source = "live_stream"

            return jsonify({
                "type": "chart_history",
                "symbol": symbol,
                "interval": interval,
                "count": len(candles),
                "source": source,
                "error": error,
                "candles": candles
            })

        # -------------------------------------------------

        @self.blueprint.route("/symbol_search", methods=["GET"])
        def symbol_search():

            query = request.args.get("query", "").strip()
            limit = int(request.args.get("limit", 20))
            exchanges = request.args.getlist("exchange") or None

            if not query:
                return jsonify({
                    "type": "symbol_search",
                    "query": query,
                    "results": []
                })

            if not self.market_feed or not hasattr(self.market_feed, "search_instruments"):
                return jsonify({
                    "error": "symbol search unavailable for active broker"
                }), 501

            try:
                results = self.market_feed.search_instruments(
                    query=query,
                    limit=limit,
                    exchanges=exchanges
                )
            except Exception as exc:
                return jsonify({
                    "error": str(exc)
                }), 500

            return jsonify({
                "type": "symbol_search",
                "query": query,
                "count": len(results),
                "results": results
            })

        # -------------------------------------------------

        @self.blueprint.route("/watch_symbol", methods=["POST"])
        def watch_symbol():

            payload = request.get_json(silent=True) or {}
            symbol = payload.get("symbol")
            exchange = payload.get("exchange", "NSE")

            if not symbol:
                return jsonify({"error": "symbol is required"}), 400

            if not self.market_feed or not hasattr(self.market_feed, "subscribe_symbol"):
                return jsonify({
                    "error": "live symbol subscription unavailable for active broker"
                }), 501

            try:
                result = self.market_feed.subscribe_symbol(symbol=symbol, exchange=exchange)
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

            if (
                result.get("status") == "subscribed"
                and self.websocket_engine
                and hasattr(self.websocket_engine, "set_active_symbol")
            ):
                self.websocket_engine.set_active_symbol(result.get("symbol", symbol))

            status = 200 if result.get("status") == "subscribed" else 400
            return jsonify(result), status

        # -------------------------------------------------

        @self.blueprint.route("/option_chain", methods=["GET"])
        def option_chain():

            symbol = request.args.get("symbol", "NIFTY")
            exchange = request.args.get("exchange", "NSE")
            strike_count = int(request.args.get("strike_count", 12))

            if not self.market_feed or not hasattr(self.market_feed, "get_option_chain"):
                return jsonify({
                    "error": "option chain unavailable for active broker"
                }), 501

            live_tick = {}
            if self.websocket_engine:
                live_tick = self.websocket_engine.latest_market_tick.get(symbol, {})

            spot_price = live_tick.get("price") or live_tick.get("ltp")

            try:
                chain = self.market_feed.get_option_chain(
                    symbol=symbol,
                    exchange=exchange,
                    spot_price=spot_price,
                    strike_count=strike_count
                )
            except Exception as exc:
                return jsonify({"error": str(exc)}), 500

            return jsonify({
                "type": "option_chain",
                **chain
            })

    # -------------------------------------------------

    def get_blueprint(self):
        return self.blueprint
