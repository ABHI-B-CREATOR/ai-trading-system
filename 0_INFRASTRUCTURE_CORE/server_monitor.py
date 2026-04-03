import time
import threading
import logging
from datetime import datetime, timedelta


TICK_TIMEOUT_SEC = 10
LOOP_MONITOR_INTERVAL = 2


class ServerMonitor:

    def __init__(self):
        self.last_tick_time = datetime.now()
        self.running = True
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("server_monitor")
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler("server_monitor.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        return logger

    # 👇 This will be called by tick engine later
    def update_tick_timestamp(self):
        self.last_tick_time = datetime.now()

    def start(self):
        self.logger.info("[SATELLITE] Server Monitor Started")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_tick_delay()
                self._check_loop_latency()
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")

            time.sleep(LOOP_MONITOR_INTERVAL)

    def _check_tick_delay(self):
        now = datetime.now()
        delay = (now - self.last_tick_time).total_seconds()

        if delay > TICK_TIMEOUT_SEC:
            self.logger.warning(
                f"[TICK] Tick Delay Detected -> {delay:.2f} sec"
            )

    def _check_loop_latency(self):
        start = time.time()
        time.sleep(0.01)
        latency = (time.time() - start) * 1000

        if latency > 100:
            self.logger.warning(
                f"[LAG] Event Loop Lag -> {latency:.2f} ms"
            )

    def stop(self):
        self.running = False
        self.logger.info("[STOP] Server Monitor Stopped")


if __name__ == "__main__":
    monitor = ServerMonitor()
    monitor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()