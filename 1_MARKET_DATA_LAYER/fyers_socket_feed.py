import websocket
import threading
import json
import time
import logging
from datetime import datetime


logger = logging.getLogger("FYERS_SOCKET")


class FyersSocketFeed:

    def __init__(self, access_token, symbols, tick_callback, strategies=None):
        """
        access_token : fyers auth token
        symbols      : list of symbols to subscribe
        tick_callback: function reference from tick_store_service
        strategies   : list of strategy instances for signal generation
        """

        self.access_token = access_token
        self.symbols = symbols
        self.tick_callback = tick_callback
        self.strategies = strategies or []  # ===== STRATEGY INJECTION =====

        self.ws = None
        self.ws_thread = None

        self.is_running = False
        self.last_heartbeat = None

        self.socket_url = (
            f"wss://api.fyers.in/socket/v2/data?access_token={self.access_token}"
        )

    # -------------------------------------------------
    # WebSocket Event Handlers
    # -------------------------------------------------

    def _on_open(self, ws):
        logger.info("FYERS SOCKET CONNECTED")

        sub_msg = {
            "symbol": self.symbols,
            "data_type": "symbolData"
        }

        ws.send(json.dumps(sub_msg))
        self.last_heartbeat = datetime.now()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)

            self.last_heartbeat = datetime.now()

            # Pass raw tick to the app callback first; it enriches and routes the
            # event through the shared strategy pipeline.
            if self.tick_callback:
                self.tick_callback(data)
            else:
                # ===== DISPATCH TO STRATEGIES =====
                self._dispatch_to_strategies(data)

        except Exception as e:
            logger.error(f"Tick Parse Error: {e}")

    def _on_error(self, ws, error):
        logger.error(f"Socket Error: {error}")

    def _on_close(self, ws, code, msg):
        logger.warning(f"Socket Closed: {code} {msg}")
        self._reconnect()

    # -------------------------------------------------
    # Connection Control
    # -------------------------------------------------

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self._connect()

        # heartbeat monitor thread
        threading.Thread(
            target=self._heartbeat_monitor,
            daemon=True
        ).start()

    def _connect(self):
        logger.info("Connecting FYERS SOCKET...")

        self.ws = websocket.WebSocketApp(
            self.socket_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        self.ws_thread = threading.Thread(
            target=self.ws.run_forever,
            daemon=True
        )
        self.ws_thread.start()

    def _reconnect(self):
        if not self.is_running:
            return

        logger.info("Reconnecting in 3 sec...")
        time.sleep(3)
        self._connect()

    def stop(self):
        self.is_running = False
        if self.ws:
            self.ws.close()

    # -------------------------------------------------
    # Heartbeat Monitor
    # -------------------------------------------------

    def _heartbeat_monitor(self):
        while self.is_running:
            try:
                if self.last_heartbeat:
                    delta = (datetime.now() - self.last_heartbeat).seconds

                    if delta > 10:
                        logger.warning("Socket Heartbeat Lost — Reconnecting")
                        self._reconnect()

                time.sleep(5)

            except Exception as e:
                logger.error(f"Heartbeat Monitor Error: {e}")

    # -------------------------------------------------
    # Strategy Dispatch
    # -------------------------------------------------

    def _dispatch_to_strategies(self, tick):
        """Send tick data to all registered strategies"""
        for strat in self.strategies:
            try:
                strat.on_market_data(tick)
            except Exception as e:
                logger.error(f"Strategy Error {strat.strategy_name} → {e}")
