import threading
from typing import Dict

import zmq

from communication.zmq_manager import ZMQManager
from config.settings import BINANCE_USD_M_FUTURES_CONFIG, ZMQ_CONFIG
from utils.logger import logger


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
        logger.info("MarketDataProcessor initialized.")

    def _process_trade_data(self, data: Dict):
        """
        Processes incoming trade data.
        (Placeholder for future implementation)
        """
        logger.info(f"Received trade data: {data}")
        # TODO: Implement trade data processing logic (e.g., create bars, calculate volume)

    def _process_depth_data(self, data: Dict):
        """
        Processes incoming order book depth data.
        (Placeholder for future implementation)
        """
        logger.info(f"Received depth data: {data}")
        # TODO: Implement order book processing logic (e.g., calculate VWAP, detect imbalances)

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
            logger.info("MarketDataProcessor listening for messages...")
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
        logger.success("MarketDataProcessor listener stopped.")
