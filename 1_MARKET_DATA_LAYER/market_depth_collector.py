import logging
import threading
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger("MARKET_DEPTH")


class MarketDepthCollector:

    def __init__(self, depth_buffer=200):
        """
        depth_buffer : number of snapshots stored per symbol
        """

        self.lock = threading.Lock()

        # symbol → rolling orderbook snapshots
        self.depth_state = defaultdict(lambda: deque(maxlen=depth_buffer))

        # symbol → latest imbalance metric
        self.imbalance_state = {}

        self.total_updates = 0
        self.last_update_time = None

    # -------------------------------------------------
    # ENTRY FROM SOCKET / DEPTH STREAM
    # -------------------------------------------------
    def on_depth_update(self, depth_tick):
        """
        depth_tick expected format:
        {
            symbol,
            bids: [(price, qty), ...],
            asks: [(price, qty), ...]
        }
        """

        try:
            symbol = depth_tick.get("symbol")
            bids = depth_tick.get("bids", [])
            asks = depth_tick.get("asks", [])

            if not symbol:
                return

            snapshot = self._build_snapshot(bids, asks)

            with self.lock:
                self.depth_state[symbol].append(snapshot)
                self.imbalance_state[symbol] = snapshot["imbalance"]

            self.total_updates += 1
            self.last_update_time = datetime.now()

        except Exception as e:
            logger.error(f"Depth Update Error: {e}")

    # -------------------------------------------------
    # SNAPSHOT BUILDER
    # -------------------------------------------------
    def _build_snapshot(self, bids, asks):

        bid_qty = sum(q for _, q in bids[:5])
        ask_qty = sum(q for _, q in asks[:5])

        imbalance = None
        if ask_qty > 0:
            imbalance = bid_qty / ask_qty

        spread = None
        if bids and asks:
            spread = asks[0][0] - bids[0][0]

        return {
            "bid_top": bids[:5],
            "ask_top": asks[:5],
            "bid_qty": bid_qty,
            "ask_qty": ask_qty,
            "imbalance": imbalance,
            "spread": spread,
            "timestamp": datetime.now()
        }

    # -------------------------------------------------
    # MICROSTRUCTURE SIGNALS
    # -------------------------------------------------
    def get_liquidity_signal(self, symbol):

        snapshots = self.depth_state.get(symbol)

        if not snapshots or len(snapshots) < 5:
            return "NEUTRAL"

        recent = list(snapshots)[-5:]

        avg_imb = sum([s["imbalance"] or 1 for s in recent]) / len(recent)

        if avg_imb > 1.3:
            return "BUY_PRESSURE"

        if avg_imb < 0.7:
            return "SELL_PRESSURE"

        return "BALANCED"

    def get_spread_state(self, symbol):

        snapshots = self.depth_state.get(symbol)

        if not snapshots:
            return None

        spreads = [s["spread"] for s in snapshots if s["spread"]]

        if not spreads:
            return None

        avg_spread = sum(spreads) / len(spreads)

        if avg_spread > 1:
            return "WIDE"

        return "TIGHT"

    # -------------------------------------------------
    # FAST FETCH
    # -------------------------------------------------
    def get_latest_depth(self, symbol):
        buf = self.depth_state.get(symbol)
        if not buf:
            return None
        return buf[-1]

    def get_depth_stats(self):
        return {
            "total_updates": self.total_updates,
            "last_update_time": self.last_update_time
        }