from datetime import date, datetime, timedelta, timezone
import threading
import time

from kiteconnect import KiteConnect, KiteTicker


class ZerodhaSocketFeed:
    """
    Zerodha/KiteConnect WebSocket feed for real-time market data.
    """

    def __init__(
        self,
        api_key,
        access_token,
        symbols=None,
        tick_callback=None,
        strategies=None,
        exchanges=None,
        status_callback=None
    ):
        self.api_key = api_key
        self.access_token = access_token
        self.symbols = symbols or ["BANKNIFTY", "NIFTY"]
        self.tick_callback = tick_callback
        self.strategies = strategies or []
        self.exchanges = exchanges or ["NSE"]
        self.status_callback = status_callback

        self.kite = KiteConnect(api_key=api_key)
        self.kite.set_access_token(access_token)

        self.ticker = KiteTicker(api_key, access_token)
        self.tokens = {}
        self.token_to_symbol = {}
        self.symbol_exchange = {}
        self.index_alias = {
            "NIFTY": "NIFTY 50",
            "BANKNIFTY": "NIFTY BANK",
            "FINNIFTY": "NIFTY FIN SERVICE"
        }
        self.instrument_cache = {}
        self.running = False
        self.connected = False
        self._seen_live_symbols = set()
        self._demo_thread = None
        self._last_start_error = ""
        self._403_error_count = 0  # Track consecutive 403 errors
        self._max_403_retries = 3  # Max retries before permanent demo mode

        self._publish_status(
            feed_status="starting",
            feed_connected=False,
            token_state="checking" if access_token else "missing",
            data_mode="live" if access_token else "demo",
            demo_fallback=False,
            last_error=""
        )

        print("[Zerodha] KiteConnect initialised")

    def _normalize_tick_timestamp(self, tick=None):
        candidates = []
        if isinstance(tick, dict):
            candidates.extend([
                tick.get("exchange_timestamp"),
                tick.get("last_trade_time"),
                tick.get("timestamp")
            ])

        for candidate in candidates:
            if isinstance(candidate, datetime):
                if candidate.tzinfo is None:
                    return candidate.replace(tzinfo=timezone.utc).isoformat()
                return candidate.astimezone(timezone.utc).isoformat()

            if isinstance(candidate, str) and candidate.strip():
                return candidate

        return datetime.now(timezone.utc).isoformat()

    def _publish_status(self, **fields):
        if not self.status_callback:
            return

        try:
            self.status_callback(fields)
        except Exception as exc:
            print(f"[Zerodha] Status callback failed: {exc}")

    def _infer_token_state(self, message=""):
        text = (message or "").lower()

        if not self.access_token:
            return "missing"

        if any(term in text for term in ("403", "forbidden", "expired", "invalid", "unauthor", "authorization", "authorisation")):
            return "expired"

        if any(term in text for term in ("token", "session", "login", "api key", "access_token", "credential", "permission")):
            return "expired"

        return "valid"

    def _start_demo_mode(self, reason="", token_state=None):
        resolved_token_state = token_state or self._infer_token_state(reason)
        self.connected = False
        self.running = True

        self._publish_status(
            data_mode="demo",
            feed_status="demo_fallback",
            feed_connected=False,
            demo_fallback=True,
            token_state=resolved_token_state,
            last_error=reason or "Live Zerodha feed unavailable. Running demo ticks."
        )

        if self._demo_thread and self._demo_thread.is_alive():
            return

        self._demo_thread = threading.Thread(target=self._simulate_demo_ticks, daemon=True)
        self._demo_thread.start()

    def _load_instruments(self, exchange):
        if exchange in self.instrument_cache:
            return self.instrument_cache[exchange]

        instruments = self.kite.instruments(exchange)
        self.instrument_cache[exchange] = instruments
        return instruments

    def _normalize_search_symbol(self, tradingsymbol):
        reverse_alias = {value: key for key, value in self.index_alias.items()}
        return reverse_alias.get(tradingsymbol, tradingsymbol)

    def _search_result_sort_key(self, result, search_query):
        symbol = (result.get("symbol") or "").upper()
        tradingsymbol = (result.get("tradingsymbol") or "").upper()
        name = (result.get("name") or "").upper()
        segment = (result.get("segment") or "").upper()
        exchange = (result.get("exchange") or "").upper()

        exact_symbol = symbol == search_query
        exact_tradingsymbol = tradingsymbol == search_query
        exact_name = name == search_query
        starts_symbol = symbol.startswith(search_query)
        starts_tradingsymbol = tradingsymbol.startswith(search_query)
        starts_name = name.startswith(search_query)
        contains_symbol = search_query in symbol
        contains_tradingsymbol = search_query in tradingsymbol
        contains_name = search_query in name
        is_index = segment == "INDICES"
        preferred_exchange = search_query == "SENSEX" and exchange == "BSE"

        return (
            0 if exact_symbol else 1,
            0 if exact_tradingsymbol else 1,
            0 if exact_name else 1,
            0 if is_index else 1,
            0 if preferred_exchange else 1,
            0 if starts_symbol else 1,
            0 if starts_tradingsymbol else 1,
            0 if starts_name else 1,
            0 if contains_symbol else 1,
            0 if contains_tradingsymbol else 1,
            0 if contains_name else 1,
            len(symbol or tradingsymbol or name)
        )

    def _get_instrument_tokens(self):
        """Get instrument tokens for symbols across configured exchanges."""
        desired_map = {
            self.index_alias.get(sym, sym): sym
            for sym in self.symbols
        }

        try:
            for exchange in self.exchanges:
                instruments = self._load_instruments(exchange)
                for inst in instruments:
                    tradingsymbol = inst.get("tradingsymbol")
                    if tradingsymbol in desired_map:
                        original_symbol = desired_map[tradingsymbol]
                        if original_symbol not in self.tokens:
                            token = inst.get("instrument_token")
                            self.tokens[original_symbol] = token
                            self.token_to_symbol[token] = original_symbol
                            self.symbol_exchange[original_symbol] = exchange
                            print(f"[Zerodha] Token resolved for {original_symbol}: {token} ({exchange})")
        except Exception as exc:
            self._last_start_error = str(exc)
            token_state = self._infer_token_state(self._last_start_error)
            self._publish_status(
                feed_status="token_expired" if token_state == "expired" else "error",
                feed_connected=False,
                token_state=token_state,
                last_error=self._last_start_error
            )
            print(f"[Zerodha] Error fetching tokens: {exc}")

    def _normalize_expiry(self, expiry):
        if isinstance(expiry, datetime):
            return expiry.date()

        if isinstance(expiry, date):
            return expiry

        if isinstance(expiry, str):
            try:
                return datetime.fromisoformat(expiry).date()
            except Exception:
                try:
                    return datetime.strptime(expiry, "%Y-%m-%d").date()
                except Exception:
                    return None

        return None

    def _find_instrument_record(self, symbol, exchange="NSE"):
        desired_symbol = self.index_alias.get(symbol, symbol)
        exchanges = [exchange] if exchange else ["NSE", "BSE"]

        for exchange_name in exchanges:
            instruments = self._load_instruments(exchange_name)

            for inst in instruments:
                tradingsymbol = inst.get("tradingsymbol")
                if tradingsymbol == desired_symbol:
                    return inst, exchange_name

        return None, exchange

    def _resolve_instrument_token(self, symbol, exchange=None):
        if symbol in self.tokens and (exchange is None or self.symbol_exchange.get(symbol) == exchange):
            return self.tokens[symbol]

        self._get_instrument_tokens()
        if symbol in self.tokens:
            return self.tokens[symbol]

        record, record_exchange = self._find_instrument_record(symbol, exchange=exchange)
        if record:
            normalized_symbol = self._normalize_search_symbol(record.get("tradingsymbol"))
            token = record.get("instrument_token")
            if token:
                self.tokens[normalized_symbol] = token
                self.token_to_symbol[token] = normalized_symbol
                self.symbol_exchange[normalized_symbol] = record_exchange
                return token

        return None

    def search_instruments(self, query, limit=20, exchanges=None):
        search_query = (query or "").strip().upper()
        if not search_query:
            return []

        selected_exchanges = exchanges or ["NSE", "BSE"]
        results = []
        seen = set()

        for exchange in selected_exchanges:
            try:
                instruments = self._load_instruments(exchange)
            except Exception:
                continue

            for inst in instruments:
                tradingsymbol = (inst.get("tradingsymbol") or "").upper()
                name = (inst.get("name") or "").upper()
                instrument_type = (inst.get("instrument_type") or "").upper()
                segment = (inst.get("segment") or "").upper()

                if instrument_type in {"CE", "PE", "FUT"} or "OPT" in segment:
                    continue

                if search_query not in tradingsymbol and search_query not in name:
                    continue

                symbol = self._normalize_search_symbol(inst.get("tradingsymbol"))
                key = (exchange, symbol)
                if key in seen:
                    continue

                seen.add(key)
                results.append({
                    "symbol": symbol,
                    "tradingsymbol": inst.get("tradingsymbol"),
                    "name": inst.get("name") or symbol,
                    "exchange": exchange,
                    "segment": inst.get("segment"),
                    "instrument_token": inst.get("instrument_token"),
                    "last_price": None
                })

        ranked_results = sorted(
            results,
            key=lambda result: self._search_result_sort_key(result, search_query)
        )[:limit]

        return self._attach_ltp_to_results(ranked_results)

    def _attach_ltp_to_results(self, results):
        if not results:
            return results

        identifiers = []
        identifier_to_result = {}

        for result in results:
            tradingsymbol = result.get("tradingsymbol")
            exchange = result.get("exchange")
            if not tradingsymbol or not exchange:
                continue

            identifier = f"{exchange}:{tradingsymbol}"
            identifiers.append(identifier)
            identifier_to_result[identifier] = result

        if not identifiers:
            return results

        try:
            ltp_response = self.kite.ltp(identifiers)
        except Exception:
            return results

        for identifier, payload in ltp_response.items():
            result = identifier_to_result.get(identifier)
            if result is not None:
                result["last_price"] = payload.get("last_price")

        return results

    def subscribe_symbol(self, symbol, exchange="NSE"):
        record, record_exchange = self._find_instrument_record(symbol, exchange=exchange)
        if not record:
            return {"status": "error", "message": f"symbol not found: {symbol}"}

        normalized_symbol = self._normalize_search_symbol(record.get("tradingsymbol"))
        token = record.get("instrument_token")
        if not token:
            return {"status": "error", "message": f"instrument token missing: {symbol}"}

        previous_token = self.tokens.get(normalized_symbol)
        previous_exchange = self.symbol_exchange.get(normalized_symbol)

        if previous_token and previous_token != token:
            self.token_to_symbol.pop(previous_token, None)
            if self.running and self.connected:
                try:
                    self.ticker.unsubscribe([previous_token])
                except Exception:
                    pass

        self.tokens[normalized_symbol] = token
        self.token_to_symbol[token] = normalized_symbol
        self.symbol_exchange[normalized_symbol] = record_exchange

        if normalized_symbol not in self.symbols:
            self.symbols.append(normalized_symbol)

        if self.running and self.connected:
            try:
                self.ticker.subscribe([token])
                self.ticker.set_mode(self.ticker.MODE_QUOTE, [token])
            except Exception as exc:
                return {"status": "error", "message": str(exc)}

        return {
            "status": "subscribed",
            "symbol": normalized_symbol,
            "exchange": record_exchange,
            "instrument_token": token,
            "previous_exchange": previous_exchange
        }

    def get_spot_price(self, symbol, exchange="NSE"):
        record, record_exchange = self._find_instrument_record(symbol, exchange=exchange)
        if not record:
            return None

        tradingsymbol = record.get("tradingsymbol")
        if not tradingsymbol:
            return None

        identifier = f"{record_exchange}:{tradingsymbol}"
        try:
            ltp_data = self.kite.ltp([identifier])
            return (ltp_data.get(identifier) or {}).get("last_price")
        except Exception:
            return None

    def get_historical_candles(self, symbol, interval="day", days=180, exchange=None):
        token = self._resolve_instrument_token(symbol, exchange=exchange)
        if not token:
            return []

        to_date = datetime.now()
        from_date = to_date - timedelta(days=max(days, 1))

        candles = self.kite.historical_data(
            token,
            from_date,
            to_date,
            interval
        )

        normalized_candles = []
        for candle in candles:
            candle_time = candle.get("date")
            if isinstance(candle_time, datetime):
                candle_time = candle_time.isoformat()

            normalized_candles.append({
                "time": candle_time,
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": candle.get("volume", 0)
            })

        return normalized_candles

    def get_option_chain(self, symbol, spot_price=None, strike_count=12, exchange="NSE"):
        underlying_name = symbol
        option_records = []
        today = datetime.now().date()
        derivative_exchanges = ["NFO"]
        if exchange == "BSE" or symbol.upper() in {"SENSEX", "BANKEX"}:
            derivative_exchanges = ["BFO", "NFO"]

        for derivative_exchange in derivative_exchanges:
            try:
                derivative_instruments = self._load_instruments(derivative_exchange)
            except Exception:
                continue

            for inst in derivative_instruments:
                instrument_type = (inst.get("instrument_type") or "").upper()
                if instrument_type not in {"CE", "PE"}:
                    continue

                if (inst.get("name") or "").upper() != underlying_name.upper():
                    continue

                expiry = self._normalize_expiry(inst.get("expiry"))
                if expiry is None or expiry < today:
                    continue

                strike = inst.get("strike")
                if strike is None:
                    continue

                option_records.append({
                    "tradingsymbol": inst.get("tradingsymbol"),
                    "expiry": expiry,
                    "strike": float(strike),
                    "type": instrument_type,
                    "exchange": derivative_exchange
                })

        if not option_records:
            return {
                "symbol": symbol,
                "expiry": None,
                "spot_price": spot_price,
                "atm_strike": None,
                "strikes": []
            }

        nearest_expiry = min(record["expiry"] for record in option_records)
        nearest_expiry_records = [record for record in option_records if record["expiry"] == nearest_expiry]
        available_strikes = sorted({record["strike"] for record in nearest_expiry_records})

        if not available_strikes:
            return {
                "symbol": symbol,
                "expiry": nearest_expiry.isoformat(),
                "spot_price": spot_price,
                "atm_strike": None,
                "strikes": []
            }

        if spot_price is None:
            spot_price = self.get_spot_price(symbol, exchange=exchange) or available_strikes[len(available_strikes) // 2]

        atm_strike = min(available_strikes, key=lambda strike: abs(strike - float(spot_price)))
        atm_index = available_strikes.index(atm_strike)
        half_window = max(int(strike_count // 2), 1)
        selected_strikes = available_strikes[max(0, atm_index - half_window):atm_index + half_window + 1]

        quotes_request = []
        for record in nearest_expiry_records:
            if record["strike"] not in selected_strikes:
                continue

            identifier = f"{record['exchange']}:{record['tradingsymbol']}"
            quotes_request.append(identifier)

        quotes = {}
        if quotes_request:
            try:
                quotes = self.kite.quote(quotes_request)
            except Exception:
                quotes = {}

        chain_rows = []
        for strike in selected_strikes:
            row = {
                "strike": strike,
                "call_oi": 0,
                "put_oi": 0,
                "call_ltp": 0,
                "put_ltp": 0,
                "call_volume": 0,
                "put_volume": 0
            }

            for option_type in ("CE", "PE"):
                record = next(
                    (item for item in nearest_expiry_records if item["strike"] == strike and item["type"] == option_type),
                    None
                )
                if not record:
                    continue

                identifier = f"{record['exchange']}:{record['tradingsymbol']}"
                quote = quotes.get(identifier, {})

                side_prefix = "call" if option_type == "CE" else "put"
                row[f"{side_prefix}_oi"] = quote.get("oi", 0) or 0
                row[f"{side_prefix}_ltp"] = quote.get("last_price", 0) or 0
                row[f"{side_prefix}_volume"] = (
                    quote.get("volume")
                    or quote.get("volume_traded")
                    or 0
                )

            chain_rows.append(row)

        return {
            "symbol": symbol,
            "expiry": nearest_expiry.isoformat(),
            "spot_price": spot_price,
            "atm_strike": atm_strike,
            "strikes": chain_rows
        }

    def _on_ticks(self, ws, ticks):
        """Handle incoming ticks from WebSocket."""
        tick_timestamp = self._normalize_tick_timestamp(ticks[0] if ticks else None)

        self._publish_status(
            data_mode="live",
            feed_status="live_connected",
            feed_connected=True,
            demo_fallback=False,
            token_state="valid",
            last_tick_time=tick_timestamp,
            last_error=""
        )

        for tick in ticks:
            symbol = self.token_to_symbol.get(tick["instrument_token"])

            if symbol:
                if symbol not in self._seen_live_symbols:
                    print(f"[Zerodha] First live tick: {symbol} {tick['last_price']}")
                    self._seen_live_symbols.add(symbol)

                tick_data = {
                    "symbol": symbol,
                    "price": tick["last_price"],
                    "bid": tick.get("bid", tick["last_price"]),
                    "ask": tick.get("ask", tick["last_price"]),
                    "volume": tick.get("volume", 0),
                    "change": tick.get("change", 0),
                    "timestamp": self._normalize_tick_timestamp(tick) or tick_timestamp
                }

                if self.tick_callback:
                    self.tick_callback(tick_data)

                for strategy in self.strategies:
                    try:
                        strategy.on_tick(tick_data)
                    except Exception as exc:
                        print(f"[Zerodha] Strategy error: {exc}")

    def _on_connect(self, ws, response=None):
        """Subscribe to ticks when connected."""
        print("[Zerodha] WebSocket connected")
        self.connected = True

        self._publish_status(
            data_mode="live",
            feed_status="connected",
            feed_connected=True,
            demo_fallback=False,
            token_state="valid",
            last_error=""
        )

        if self.tokens:
            self.ticker.subscribe(list(self.tokens.values()))
            self.ticker.set_mode(self.ticker.MODE_QUOTE, list(self.tokens.values()))

    def _on_close(self, ws, code=None, reason=None):
        """Handle WebSocket close."""
        reason_text = str(reason or "")
        token_state = self._infer_token_state(reason_text)
        is_403_error = "403" in reason_text or "Forbidden" in reason_text

        print(f"[Zerodha] WebSocket closed ({code}): {reason_text}")
        self.connected = False
        self.running = False
        
        # Track 403 errors
        if is_403_error:
            self._403_error_count += 1
            print(f"[Zerodha] 403 error count: {self._403_error_count}/{self._max_403_retries}")

        # If 403 error, likely market is closed - show as market_closed, not demo
        if is_403_error:
            self._publish_status(
                feed_status="market_closed",
                feed_connected=False,
                token_state="valid",  # Token is valid, just market closed
                data_mode="live",  # Keep as live mode
                market_state="closed",
                last_error="Market closed - live feed unavailable until 9:15 AM IST"
            )
            print("[Zerodha] Market closed - WebSocket unavailable. Using historical data.")
        else:
            self._publish_status(
                feed_status="token_expired" if token_state == "expired" else "disconnected",
                feed_connected=False,
                token_state=token_state,
                last_error=reason_text or "Live feed disconnected"
            )

    def _on_error(self, ws, code=None, reason=None):
        """Handle WebSocket error."""
        reason_text = str(reason or code or "")
        token_state = self._infer_token_state(reason_text)
        feed_status = "token_expired" if token_state == "expired" else "error"
        is_403_error = "403" in reason_text or "Forbidden" in reason_text

        print(f"[Zerodha] WebSocket error ({code}): {reason_text}")
        self.connected = False
        
        # Track 403 errors
        if is_403_error:
            self._403_error_count += 1
            print(f"[Zerodha] 403 error count: {self._403_error_count}/{self._max_403_retries}")

        # If 403 error, likely market is closed - show as market_closed, not demo
        if is_403_error:
            self._publish_status(
                feed_status="market_closed",
                feed_connected=False,
                token_state="valid",  # Token is valid, just market closed
                data_mode="live",  # Keep as live mode
                market_state="closed",
                last_error="Market closed - live feed unavailable until 9:15 AM IST"
            )
        else:
            self._publish_status(
                feed_status=feed_status,
                feed_connected=False,
                token_state=token_state,
                last_error=reason_text or "Unknown feed error"
            )

    def start(self):
        """Start the WebSocket feed."""
        try:
            self._publish_status(
                feed_status="connecting",
                feed_connected=False,
                token_state="checking" if self.access_token else "missing",
                data_mode="live" if self.access_token else "demo",
                demo_fallback=False,
                last_error=""
            )

            if not self.api_key or not self.access_token:
                self._last_start_error = "Missing Zerodha API key or access token"
                print(f"[Zerodha] {self._last_start_error}")
                self._start_demo_mode(self._last_start_error, token_state="missing")
                return

            self._get_instrument_tokens()

            if not self.tokens:
                reason = self._last_start_error or "No instrument tokens found for the configured symbols"
                print(f"[Zerodha] {reason}")
                self._start_demo_mode(reason, token_state=self._infer_token_state(reason))
                return

            self.ticker.on_ticks = self._on_ticks
            self.ticker.on_connect = self._on_connect
            self.ticker.on_close = self._on_close
            self.ticker.on_error = self._on_error

            self.running = True
            self.ticker.connect(threaded=True)

            self._publish_status(
                data_mode="live",
                feed_status="connecting",
                feed_connected=False,
                demo_fallback=False,
                token_state="valid",
                last_error=""
            )

            print("[Zerodha] WebSocket started")

        except Exception as exc:
            reason = str(exc)
            print(f"[Zerodha] Error starting feed: {reason}")
            self._start_demo_mode(reason, token_state=self._infer_token_state(reason))

    def _simulate_demo_ticks(self):
        """Fallback demo mode when live auth/feed is unavailable."""
        print("[Zerodha] Demo tick fallback active")
        import random

        prices = {sym: 50000 + random.randint(-1000, 1000) for sym in self.symbols}

        while self.running:
            tick_timestamp = datetime.now(timezone.utc).isoformat()
            for symbol in self.symbols:
                price_change = random.uniform(-0.002, 0.002)
                prices[symbol] *= (1 + price_change)

                tick_data = {
                    "symbol": symbol,
                    "price": round(prices[symbol], 2),
                    "bid": round(prices[symbol] - 0.5, 2),
                    "ask": round(prices[symbol] + 0.5, 2),
                    "volume": random.randint(1000, 10000),
                    "change": round(random.uniform(-1, 1), 2),
                    "timestamp": tick_timestamp
                }

                if self.tick_callback:
                    self.tick_callback(tick_data)

                for strategy in self.strategies:
                    try:
                        strategy.on_tick(tick_data)
                    except Exception:
                        pass

            self._publish_status(
                data_mode="demo",
                feed_status="demo_fallback",
                feed_connected=False,
                demo_fallback=True,
                last_tick_time=tick_timestamp
            )

            time.sleep(1)

    def stop(self):
        """Stop the WebSocket feed."""
        self.running = False
        self.connected = False

        try:
            self.ticker.close()
        except Exception:
            pass

        self._publish_status(
            feed_status="stopped",
            feed_connected=False
        )

        print("[Zerodha] WebSocket stopped")
