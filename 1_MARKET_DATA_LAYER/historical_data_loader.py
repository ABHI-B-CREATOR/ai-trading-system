import logging
import pandas as pd
from datetime import datetime, timedelta
import os

logger = logging.getLogger("HIST_DATA")


class HistoricalDataLoader:

    def __init__(self, data_path="historical_data"):
        """
        data_path : root folder where historical csv/parquet stored
        """
        self.data_path = data_path

        # symbol → dataframe cache
        self.cache = {}

        self.last_load_time = None
        self.total_symbols_loaded = 0

    # -------------------------------------------------
    # MAIN LOAD FUNCTION
    # -------------------------------------------------
    def load_symbol_history(self, symbol, timeframe="1min", days=5):

        try:
            file_path = self._build_file_path(symbol, timeframe)

            if not os.path.exists(file_path):
                logger.warning(f"Historical file missing: {file_path}")
                return None

            df = pd.read_csv(file_path)

            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("datetime")

            cutoff = datetime.now() - timedelta(days=days)
            df = df[df["datetime"] >= cutoff]

            self.cache[symbol] = df

            self.total_symbols_loaded += 1
            self.last_load_time = datetime.now()

            logger.info(f"Loaded history: {symbol}")

            return df

        except Exception as e:
            logger.error(f"Historical Load Error: {e}")
            return None

    # -------------------------------------------------
    # BULK LOAD
    # -------------------------------------------------
    def bulk_load(self, symbols, timeframe="1min", days=5):

        results = {}

        for sym in symbols:
            df = self.load_symbol_history(sym, timeframe, days)
            if df is not None:
                results[sym] = df

        return results

    # -------------------------------------------------
    # GAP FILL UTILITY
    # -------------------------------------------------
    def fill_session_gap(self, df):

        try:
            df = df.set_index("datetime")

            full_index = pd.date_range(
                start=df.index.min(),
                end=df.index.max(),
                freq="1min"
            )

            df = df.reindex(full_index)
            df = df.ffill()  # Use ffill() instead of deprecated fillna(method="ffill")

            df.reset_index(inplace=True)
            df.rename(columns={"index": "datetime"}, inplace=True)

            return df

        except Exception as e:
            logger.error(f"Gap Fill Error: {e}")
            return df

    # -------------------------------------------------
    # DATASET FETCH FOR AI
    # -------------------------------------------------
    def get_cached_history(self, symbol):
        return self.cache.get(symbol)

    # -------------------------------------------------
    # FILE PATH BUILDER
    # -------------------------------------------------
    def _build_file_path(self, symbol, timeframe):

        file_name = f"{symbol}_{timeframe}.csv"
        return os.path.join(self.data_path, file_name)

    # -------------------------------------------------
    # HEALTH
    # -------------------------------------------------
    def get_loader_stats(self):
        return {
            "total_symbols_loaded": self.total_symbols_loaded,
            "last_load_time": self.last_load_time
        }