import logging
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger("CANDLE_BUILDER")


class CandleBuilder:

    def __init__(self, timeframes=(60, 300, 900), history_limit=500):
        """
        timeframes : tuple in seconds (default 1m, 5m, 15m)
        history_limit : candles stored per symbol per timeframe
        """

        self.timeframes = timeframes

        # symbol → tf → current candle
        self.current = defaultdict(dict)

        # symbol → tf → history deque
        self.history = defaultdict(
            lambda: {tf: deque(maxlen=history_limit) for tf in timeframes}
        )

    # -------------------------------------------------
    # MAIN ENTRY
    # -------------------------------------------------
    def on_tick(self, tick):

        try:
            symbol = tick["symbol"]
            price = tick["price"]
            ts = tick["timestamp"]

            for tf in self.timeframes:
                bucket = self._get_bucket(ts, tf)

                cur = self.current[symbol].get(tf)

                # start new candle
                if cur is None:
                    self.current[symbol][tf] = self._new_candle(symbol, price, bucket)
                    continue

                # rollover
                if bucket > cur["bucket"]:
                    self._finalize(symbol, tf)
                    self.current[symbol][tf] = self._new_candle(symbol, price, bucket)

                else:
                    self._update(symbol, tf, price)

        except Exception as e:
            logger.error(f"Candle Build Error: {e}")

    # -------------------------------------------------
    # BUCKET
    # -------------------------------------------------
    def _get_bucket(self, ts, tf):

        sec = int(ts.timestamp())
        bucket = sec - (sec % tf)
        return datetime.fromtimestamp(bucket)

    # -------------------------------------------------
    # NEW
    # -------------------------------------------------
    def _new_candle(self, symbol, price, bucket):

        return {
            "symbol": symbol,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "bucket": bucket
        }

    # -------------------------------------------------
    # UPDATE
    # -------------------------------------------------
    def _update(self, symbol, tf, price):

        c = self.current[symbol][tf]

        c["high"] = max(c["high"], price)
        c["low"] = min(c["low"], price)
        c["close"] = price

    # -------------------------------------------------
    # FINALIZE
    # -------------------------------------------------
    def _finalize(self, symbol, tf):

        c = self.current[symbol][tf]
        self.history[symbol][tf].append(c)

        logger.debug(f"Candle Closed {symbol} TF {tf}: {c}")

    # -------------------------------------------------
    # FETCH APIS
    # -------------------------------------------------
    def get_latest(self, symbol, tf):

        hist = self.history.get(symbol, {}).get(tf)
        if not hist:
            return None

        return hist[-1]

    def get_history(self, symbol, tf, limit=50):

        hist = self.history.get(symbol, {}).get(tf)
        if not hist:
            return []

        return list(hist)[-limit:]