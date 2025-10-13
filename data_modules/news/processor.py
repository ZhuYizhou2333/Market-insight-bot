import threading
from typing import Dict

import zmq

from ai_analyzers.news_analyzer import NewsAnalyzer
from communication.zmq_manager import ZMQManager
from config.settings import AI_ANALYZER_CONFIG, ZMQ_CONFIG
from utils.logger import logger


class NewsProcessor:
    """
    Subscribes to raw news from ZeroMQ, processes it, and performs AI analysis.
    Runs in a separate thread and can be stopped gracefully.
    """

    def __init__(self, zmq_manager: ZMQManager):
        """
        Initializes the NewsProcessor with AI analysis capability.

        Args:
            zmq_manager: An instance of ZMQManager for subscribing to news.
        """
        self.zmq_manager = zmq_manager
        self.news_topic = ZMQ_CONFIG["NEWS_TOPIC"]
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        # 初始化 AI 分析器
        try:
            self.news_analyzer = NewsAnalyzer(
                model=AI_ANALYZER_CONFIG["MODEL"],
                message_buffer_size=AI_ANALYZER_CONFIG["MESSAGE_BUFFER_SIZE"],
                analysis_interval=AI_ANALYZER_CONFIG["ANALYSIS_INTERVAL"],
            )
            logger.info("NewsProcessor initialized with AI analyzer.")
        except Exception as e:
            logger.error(f"Failed to initialize AI analyzer: {e}")
            self.news_analyzer = None
            logger.warning("NewsProcessor will run without AI analysis.")

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
        Processes the received news data and adds it to AI analyzer.

        Args:
            news_data (dict): The news data received from the fetcher.
        """
        # 记录接收到的消息
        channel = news_data.get("channel", "Unknown")
        text = news_data.get("text", "")
        logger.info(f"Processing news from {channel}: {text[:50]}...")

        # 如果 AI 分析器可用，将消息添加到分析器
        # 分析器会自动在达到分析间隔时进行分析
        if self.news_analyzer:
            try:
                self.news_analyzer.add_message(news_data)

                # 每 100 条消息打印一次统计信息
                stats = self.news_analyzer.get_stats()
                if stats["total_messages"] % 100 == 0:
                    logger.info(
                        f"AI Analyzer Stats - Total: {stats['total_messages']}, "
                        f"Buffer: {stats['buffer_size']}, "
                        f"Next analysis at: {stats['next_analysis_at']}"
                    )
            except Exception as e:
                logger.error(f"Error adding message to AI analyzer: {e}")
