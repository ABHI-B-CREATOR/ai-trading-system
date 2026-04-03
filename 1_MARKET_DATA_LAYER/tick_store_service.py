import logging
import threading
import queue
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger("TICK_STORE")


class TickStoreService:

    def __init__(self, buffer_size=2000, queue_size=50000):
        """
        buffer_size : ticks stored per symbol for micro processing
        queue_size  : global processing queue size
        """

        self.lock = threading.Lock()

        # latest tick snapshot per symbol
        self.symbol_state = {}

        # rolling tick buffer per symbol
        self.tick_buffers = defaultdict(lambda: deque(maxlen=buffer_size))

        # downstream processing queue
        self.tick_queue = queue.Queue(maxsize=queue_size)

        self.total_ticks = 0
        self.last_tick_time = None

    # -------------------------------------------------
    # ENTRY FROM SOCKET FEED
    # -------------------------------------------------
    def on_new_tick(self, raw_tick):
        """
        callback from fyers_socket_feed
        """

        try:
            tick = self._normalize_tick(raw_tick)

            symbol = tick["symbol"]

            with self.lock:
                self.symbol_state[symbol] = tick
                self.tick_buffers[symbol].append(tick)

            # non-blocking queue push
            try:
                self.tick_queue.put_nowait(tick)
            except queue.Full:
                logger.warning("Tick Queue Full — Dropping Tick")

            self.total_ticks += 1
            self.last_tick_time = datetime.now()

        except Exception as e:
            logger.error(f"Tick Store Error: {e}")

    # -------------------------------------------------
    # NORMALIZATION
    # -------------------------------------------------
    def _normalize_tick(self, t):
        """
        Fyers raw schema → internal fast schema
        """

        return {
            "symbol": t.get("symbol"),
            "ltp": t.get("ltp"),
            "bid": t.get("bid"),
            "ask": t.get("ask"),
            "volume": t.get("vol_traded_today"),
            "exchange_time": t.get("exch_feed_time"),
            "recv_time": datetime.now()
        }

    # -------------------------------------------------
    # FAST READ APIS
    # -------------------------------------------------
    def get_latest_tick(self, symbol):
        return self.symbol_state.get(symbol)

    def get_tick_buffer(self, symbol):
        return list(self.tick_buffers.get(symbol, []))

    def get_next_tick(self, timeout=1):
        try:
            return self.tick_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # -------------------------------------------------
    # HEALTH METRICS
    # -------------------------------------------------
    def get_feed_stats(self):
        return {
            "total_ticks": self.total_ticks,
            "last_tick_time": self.last_tick_time
        }