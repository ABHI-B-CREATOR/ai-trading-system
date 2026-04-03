import logging
import threading
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("OPTION_CHAIN")


class OptionChainFetcher:

    def __init__(self):
        # symbol → strike → option_type → snapshot
        self.chain_state = defaultdict(lambda: defaultdict(dict))

        self.lock = threading.Lock()

        self.last_update_time = None
        self.total_updates = 0

    # -------------------------------------------------
    # ENTRY FROM SOCKET / REST POLLER
    # -------------------------------------------------
    def on_option_tick(self, raw_tick):
        """
        raw_tick expected normalized from tick_store
        must contain:
        symbol, strike, option_type (CE/PE), ltp, oi, iv, volume
        """

        try:
            symbol = raw_tick.get("symbol")
            strike = raw_tick.get("strike")
            opt_type = raw_tick.get("option_type")

            if not symbol or strike is None or not opt_type:
                return

            snapshot = self._build_snapshot(raw_tick)

            with self.lock:
                self.chain_state[symbol][strike][opt_type] = snapshot

            self.total_updates += 1
            self.last_update_time = datetime.now()

        except Exception as e:
            logger.error(f"Option Chain Update Error: {e}")

    # -------------------------------------------------
    # SNAPSHOT BUILDER
    # -------------------------------------------------
    def _build_snapshot(self, t):

        return {
            "ltp": t.get("ltp"),
            "oi": t.get("oi"),
            "oi_change": t.get("oi_change"),
            "iv": t.get("iv"),
            "volume": t.get("volume"),
            "bid": t.get("bid"),
            "ask": t.get("ask"),
            "timestamp": datetime.now()
        }

    # -------------------------------------------------
    # FAST READ APIS
    # -------------------------------------------------
    def get_strike_data(self, symbol, strike):
        return self.chain_state.get(symbol, {}).get(strike, {})

    def get_full_chain(self, symbol):
        return self.chain_state.get(symbol, {})

    def get_atm_strike(self, symbol, spot_price):
        """
        finds nearest strike to spot
        """
        strikes = self.chain_state.get(symbol, {}).keys()

        if not strikes:
            return None

        return min(strikes, key=lambda x: abs(x - spot_price))

    # -------------------------------------------------
    # DERIVATIVE SENTIMENT METRICS
    # -------------------------------------------------
    def get_pcr_oi(self, symbol):
        """
        Put Call Ratio based on OI
        """

        ce_oi = 0
        pe_oi = 0

        chain = self.chain_state.get(symbol, {})

        for strike_data in chain.values():
            ce = strike_data.get("CE")
            pe = strike_data.get("PE")

            if ce:
                ce_oi += ce.get("oi", 0)

            if pe:
                pe_oi += pe.get("oi", 0)

        if ce_oi == 0:
            return None

        return pe_oi / ce_oi

    # -------------------------------------------------
    # HEALTH
    # -------------------------------------------------
    def get_chain_stats(self):
        return {
            "total_updates": self.total_updates,
            "last_update_time": self.last_update_time
        }