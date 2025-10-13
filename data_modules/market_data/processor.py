import threading
import time
from typing import Any, Dict

import zmq

from communication.zmq_manager import ZMQManager
from config.settings import BINANCE_USD_M_FUTURES_CONFIG, ZMQ_CONFIG
from utils.logger import logger


class MonitoredCache:
    """自定义带监控的缓存，支持过期和日志记录，由独立线程监控过期"""

    def __init__(self, maxsize: int, ttl: float):
        self.maxsize = maxsize
        self.ttl = ttl
        self._data = {}  # key: (value, timestamp)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_expiry, daemon=True
        )
        self._monitor_thread.start()

    def __setitem__(self, key: Any, value: Any) -> None:
        with self._lock:
            old = self._data.get(key)
            now = time.time()
            if old is not None and old[0] == value:
                self._data[key] = (value, now)
                return
            if old is None:
                logger.info(f"缓存新增 - 键: {key}, 值: {value}")
            self._data[key] = (value, now)
            # 控制最大容量
            if len(self._data) > self.maxsize:
                # 简单淘汰最早的
                oldest_key = min(self._data.items(), key=lambda x: x[1][1])[0]
                self.__delitem__(oldest_key)

    def __getitem__(self, key: Any) -> Any:
        with self._lock:
            return self._data[key][0]

    def get(self, key: Any):
        with self._lock:
            item = self._data.get(key)
            return item[0] if item else None

    def __delitem__(self, key: Any) -> None:
        with self._lock:
            if key in self._data:
                value = self._data[key][0]
                logger.info(f"缓存过期 - 键: {key}, 值: {value}")
                del self._data[key]

    def __contains__(self, key: Any) -> bool:
        with self._lock:
            return key in self._data

    def stop(self):
        self._stop_event.set()
        self._monitor_thread.join()

    def _monitor_expiry(self):
        while not self._stop_event.is_set():
            now = time.time()
            expired = []
            with self._lock:
                for key, (value, ts) in list(self._data.items()):
                    if now - ts > self.ttl:
                        expired.append(key)
            for key in expired:
                self.__delitem__(key)
            time.sleep(1)


class MarketDataProcessor:
    """
    Subscribes to raw market data from ZeroMQ, processes it,
    and can publish aggregated data to other topics.
    """

    def __init__(self, zmq_manager: ZMQManager):
        """
        Initializes the MarketDataProcessor.

        Args:
            zmq_manager: An instance of ZMQManager for subscribing to data.
        """
        self.zmq_manager = zmq_manager
        self.trade_topic: str = ZMQ_CONFIG["MARKET_DATA_TOPIC_TRADE"]
        self.depth_topic: str = ZMQ_CONFIG["MARKET_DATA_TOPIC_DEPTH"]
        self._stop_event = threading.Event()
        self._thread = None
        self.cache = MonitoredCache(
            maxsize=1000,  # Adjust as needed
            ttl=5,  # 5 seconds TTL
        )
        logger.info("MarketDataProcessor initialized.")

    def _process_trade_data(self, data: Dict):
        """
        Processes incoming trade data with timestamp checking.
        """
        try:
            self.cache[data["data"]["e"]] = data["data"]
            with open("logs/trade_data.log", "w") as f:
                f.write(f"{data['data']['e']}: {data['data']}\n")
        except Exception as e:
            logger.error(f"Error processing trade data: {e}", exc_info=True)

    def _process_depth_data(self, data: Dict):
        """
        Processes incoming order book depth data with timestamp checking.
        """
        try:
            self.cache[data["data"]["e"]] = data["data"]
            with open("logs/depth_data.log", "w") as f:
                f.write(f"{data['data']['e']}: {data['data']}\n")
        except Exception as e:
            logger.error(f"Error processing depth data: {e}", exc_info=True)

    def _listen(self):
        """
        The main loop for the listener thread.
        """
        # Subscribe to all sub-topics for trades and depth
        # 使用精确的主题名称

        topics_to_subscribe = []
        for symbol in BINANCE_USD_M_FUTURES_CONFIG["SYMBOLS"]:
            topics_to_subscribe.append(f"{self.trade_topic}.{symbol}")
            topics_to_subscribe.append(f"{self.depth_topic}.{symbol}")

        subscriber = self.zmq_manager.get_subscriber(
            ZMQ_CONFIG["MARKET_DATA_PUBLISHER_ADDRESS"].replace("*", "127.0.0.1"),
            topics_to_subscribe,
        )
        logger.success(f"Subscribed to topics: {topics_to_subscribe}")

        while not self._stop_event.is_set():
            try:
                # Poll with a timeout to remain responsive to the stop event
                if subscriber.poll(timeout=1000):  # 1-second timeout
                    topic, message = self.zmq_manager.receive_message(subscriber)
                    if topic.startswith(self.trade_topic):
                        self._process_trade_data(message)
                    elif topic.startswith(self.depth_topic):
                        self._process_depth_data(message)
            except zmq.ZMQError as e:
                logger.warning(
                    f"ZMQ error in MarketDataProcessor, shutting down listener: {e}"
                )
                break  # Exit loop on ZMQ error
            except Exception as e:
                logger.error(
                    f"Error in MarketDataProcessor listening loop: {e}", exc_info=True
                )

    def start_listening(self):
        """
        Starts the listener in a separate thread.
        """
        logger.info("Starting MarketDataProcessor listener...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.success("MarketDataProcessor listener started.")

    def stop_listening(self):
        """
        Stops the listener thread.
        """
        logger.info("Stopping MarketDataProcessor listener...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join()
        if hasattr(self, "cache") and hasattr(self.cache, "stop"):
            self.cache.stop()
        logger.success("MarketDataProcessor listener stopped.")
