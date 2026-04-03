import time
import psutil
import threading
import logging
from datetime import datetime

HEARTBEAT_INTERVAL = 5
CPU_ALERT_THRESHOLD = 85
RAM_ALERT_THRESHOLD = 85

class SystemHealthService:

    def __init__(self):
        self.last_heartbeat = datetime.now()
        self.running = True
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger("infra_health")
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler("infra_health.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        return logger

    def start(self):
        self.logger.info("[START] Infrastructure Health Service Started")
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self):
        while self.running:
            try:
                self._check_cpu()
                self._check_ram()
                self._heartbeat()
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")

            time.sleep(HEARTBEAT_INTERVAL)

    def _check_cpu(self):
        cpu = psutil.cpu_percent()
        if cpu > CPU_ALERT_THRESHOLD:
            self.logger.warning(f"HIGH CPU USAGE -> {cpu}%")

    def _check_ram(self):
        ram = psutil.virtual_memory().percent
        if ram > RAM_ALERT_THRESHOLD:
            self.logger.warning(f"HIGH RAM USAGE -> {ram}%")

    def _heartbeat(self):
        now = datetime.now()
        delta = (now - self.last_heartbeat).seconds
        self.logger.info(f"System heartbeat OK | delay={delta}s")
        self.last_heartbeat = now

    def stop(self):
        self.running = False
        self.logger.info("[STOP] Infrastructure Health Service Stopped")


if __name__ == "__main__":
    service = SystemHealthService()
    service.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop()