import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("CANDLE_ENGINE")


class CandleEngine:

    def __init__(self, timeframe_seconds=60, timezone_name="Asia/Kolkata"):
        self.timeframe = timeframe_seconds
        self.timezone_name = timezone_name or "Asia/Kolkata"
        try:
            self.market_timezone = ZoneInfo(self.timezone_name)
        except Exception:
            self.timezone_name = "Asia/Kolkata"
            self.market_timezone = ZoneInfo(self.timezone_name)

        # symbol → current building candle
        self.current_candles = {}

        # symbol → historical candles list
        self.candle_history = {}

    # ---------- PUBLIC ENTRY ----------
    def process_tick(self, tick):
        try:
            if not isinstance(tick, dict):
                return

            symbol = tick.get("symbol") or tick.get("tradingsymbol")
            price = (
                tick.get("price")
                or tick.get("ltp")
                or tick.get("last_price")
            )
            ts = self._parse_timestamp(
                tick.get("timestamp")
                or tick.get("time")
                or tick.get("ts")
                or tick.get("exchange_time")
                or tick.get("exch_feed_time")
            )

            if not symbol or price is None:
                return

            if ts is None:
                ts = datetime.now(self.market_timezone)

            bucket_time = self._get_bucket_time(ts)

            if symbol not in self.current_candles:
                self._start_new_candle(symbol, price, bucket_time)
                return

            current = self.current_candles[symbol]

            # candle rollover condition
            if bucket_time > current["bucket"]:
                self._finalize_candle(symbol)
                self._start_new_candle(symbol, price, bucket_time)

            else:
                self._update_candle(symbol, price)

        except Exception as e:
            logger.error(f"Candle Processing Error: {e}")

    # ---------- BUCKET CALC ----------
    def _get_bucket_time(self, timestamp):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=self.market_timezone)
        else:
            timestamp = timestamp.astimezone(self.market_timezone)

        seconds = int(timestamp.timestamp())
        bucket = seconds - (seconds % self.timeframe)
        return datetime.fromtimestamp(bucket, self.market_timezone)

    def _parse_timestamp(self, timestamp):
        if isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=self.market_timezone)
            return timestamp.astimezone(self.market_timezone)

        if isinstance(timestamp, (int, float)):
            try:
                return datetime.fromtimestamp(timestamp, self.market_timezone)
            except Exception:
                return None

        if isinstance(timestamp, str):
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=self.market_timezone)
                return parsed.astimezone(self.market_timezone)
            except Exception:
                try:
                    return datetime.fromtimestamp(float(timestamp), self.market_timezone)
                except Exception:
                    return None

        return None

    # ---------- START ----------
    def _start_new_candle(self, symbol, price, bucket):
        self.current_candles[symbol] = {
            "symbol": symbol,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "bucket": bucket
        }

    # ---------- UPDATE ----------
    def _update_candle(self, symbol, price):
        candle = self.current_candles[symbol]

        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["close"] = price

    # ---------- FINALIZE ----------
    def _finalize_candle(self, symbol):
        candle = self.current_candles[symbol]

        if symbol not in self.candle_history:
            self.candle_history[symbol] = []

        self.candle_history[symbol].append(candle)

        logger.info(f"Candle Closed: {candle}")

    # ---------- FETCH API ----------
    def get_latest_candles(self, symbol, limit=600, include_current=True):
        candles = list(self.candle_history.get(symbol, []))

        if include_current and symbol in self.current_candles:
            candles.append(self.current_candles[symbol])

        candles = candles[-limit:]
        return [self._serialize_candle(candle) for candle in candles]

    def _serialize_candle(self, candle):
        bucket = candle.get("bucket")
        if isinstance(bucket, datetime):
            bucket_time = bucket.isoformat()
        else:
            bucket_time = bucket

        return {
            "symbol": candle.get("symbol"),
            "open": candle.get("open"),
            "high": candle.get("high"),
            "low": candle.get("low"),
            "close": candle.get("close"),
            "time": bucket_time
        }
