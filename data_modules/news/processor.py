import threading
from typing import Dict

import zmq

from communication.zmq_manager import ZMQManager
from config.settings import ZMQ_CONFIG
from utils.logger import logger


class NewsProcessor:
    """
    Subscribes to raw news from ZeroMQ, processes it, and prepares it for AI analysis.
    Runs in a separate thread and can be stopped gracefully.
    """

    def __init__(self, zmq_manager: ZMQManager):
        """
        Initializes the NewsProcessor.

        Args:
            zmq_manager: An instance of ZMQManager for subscribing to news.
        """
        self.zmq_manager = zmq_manager
        self.news_topic = ZMQ_CONFIG["NEWS_TOPIC"]
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        logger.info("NewsProcessor initialized.")

    def _listen(self):
        """
        The main loop for the listener thread.
        Subscribes to the news topic and processes messages until stopped.
        """
        subscriber = self.zmq_manager.get_subscriber(
            ZMQ_CONFIG["NEWS_PUBLISHER_ADDRESS"].replace("*", "127.0.0.1"),
            [self.news_topic],
        )
        logger.info(f"NewsProcessor subscribed to ZMQ topic '{self.news_topic}'")
        logger.info("NewsProcessor is now listening for messages...")

        while not self._stop_event.is_set():
            try:
                # Poll with a timeout to remain responsive to the stop event
                if subscriber.poll(timeout=1000):  # 1-second timeout
                    _topic, message_data = self.zmq_manager.receive_message(subscriber)
                    self.process_news(message_data)
            except zmq.ZMQError as e:
                logger.warning(
                    f"ZMQ error in NewsProcessor, shutting down listener: {e}"
                )
                break  # Exit loop on ZMQ error (e.g., context terminated)
            except Exception as e:
                logger.error(
                    f"Error in NewsProcessor listening loop: {e}", exc_info=True
                )

        logger.info("NewsProcessor listener loop finished.")

    def start_listening(self):
        """
        Starts the listener in a separate daemon thread.
        """
        if self._thread is not None and self._thread.is_alive():
            logger.warning("NewsProcessor is already running.")
            return

        logger.info("Starting NewsProcessor listener...")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.success("NewsProcessor listener started.")

    def stop_listening(self):
        """
        Signals the listener thread to stop and waits for it to terminate.
        """
        if self._thread is None or not self._thread.is_alive():
            logger.info("NewsProcessor is not running.")
            return

        logger.info("Stopping NewsProcessor listener...")
        self._stop_event.set()
        self._thread.join()  # Wait for the thread to finish
        self._thread = None
        logger.success("NewsProcessor listener stopped.")

    def process_news(self, news_data: Dict):
        """
        Processes the received news data.
        This is a placeholder for more complex processing logic.

        Args:
            news_data (dict): The news data received from the fetcher.
        """
        # For now, we just log the received data.
        logger.info(f"Processing news: {news_data}")
