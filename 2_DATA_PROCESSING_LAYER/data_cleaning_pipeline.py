import logging
from datetime import datetime

logger = logging.getLogger("DATA_CLEANER")


class DataCleaningPipeline:

    def __init__(self, max_price_jump_pct=5):
        """
        max_price_jump_pct : spike threshold
        """
        self.max_jump = max_price_jump_pct / 100
        self.last_price = {}

    # -------------------------------------------------
    # MAIN ENTRY
    # -------------------------------------------------
    def clean_tick(self, tick):

        try:
            symbol = tick.get("symbol")
            ltp = tick.get("ltp")

            if symbol is None or ltp is None:
                return None

            if not self._validate_price(symbol, ltp):
                logger.warning(f"Spike filtered: {symbol} {ltp}")
                return None

            cleaned = {
                "symbol": symbol,
                "price": float(ltp),
                "bid": tick.get("bid"),
                "ask": tick.get("ask"),
                "volume": tick.get("volume"),
                "timestamp": self._normalize_time(tick)
            }

            self.last_price[symbol] = cleaned["price"]

            return cleaned

        except Exception as e:
            logger.error(f"Tick Clean Error: {e}")
            return None

    # -------------------------------------------------
    # PRICE SPIKE FILTER
    # -------------------------------------------------
    def _validate_price(self, symbol, price):

        last = self.last_price.get(symbol)

        if last is None:
            return True

        change = abs(price - last) / last

        if change > self.max_jump:
            return False

        return True

    # -------------------------------------------------
    # TIME NORMALIZATION
    # -------------------------------------------------
    def _normalize_time(self, tick):

        exch_time = tick.get("exchange_time")

        if exch_time:
            return exch_time

        return datetime.now()

    # -------------------------------------------------
    # OPTION DATA CLEANER
    # -------------------------------------------------
    def clean_option_snapshot(self, snap):

        try:
            if snap.get("iv") and snap["iv"] < 0:
                snap["iv"] = None

            if snap.get("oi") and snap["oi"] < 0:
                snap["oi"] = 0

            return snap

        except Exception as e:
            logger.error(f"Option Clean Error: {e}")
            return snap