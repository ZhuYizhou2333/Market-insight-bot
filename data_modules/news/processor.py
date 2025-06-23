import json

import zmq

from config.settings import ZMQ_CONFIG
from utils.logger import logger


class NewsProcessor:
    """
    Subscribes to raw news from ZeroMQ, processes it, and prepares it for AI analysis.
    """

    def __init__(self):
        """
        Initializes the ZeroMQ subscriber.
        """
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(ZMQ_CONFIG["NEWS_PUBLISHER_ADDRESS"])
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, ZMQ_CONFIG["NEWS_TOPIC"])
        logger.info(
            f"NewsProcessor subscribed to ZMQ topic '{ZMQ_CONFIG['NEWS_TOPIC']}' at {ZMQ_CONFIG['NEWS_PUBLISHER_ADDRESS']}"
        )

    def start_listening(self):
        """
        Starts an infinite loop to listen for and process messages.
        """
        logger.info("NewsProcessor is now listening for messages...")
        while True:
            try:
                topic, message_json = self.subscriber.recv_multipart()
                message_data = json.loads(message_json.decode("utf-8"))
                self.process_news(message_data)
            except Exception as e:
                logger.error(f"Error receiving or processing message: {e}")

    def process_news(self, news_data: dict):
        """
        Processes the received news data.
        This is a placeholder for more complex processing logic.

        Args:
            news_data (dict): The news data received from the fetcher.
        """
        # TODO: Implement the actual news processing logic here.
        # For now, we just log the received data.
        logger.info(f"Processing news: {news_data}")
        # Example of what could be done:
        # - Clean the text
        # - Extract entities
        # - Save to a database
        # - Forward to another ZMQ topic for AI analysis

    def close(self):
        """
        Closes the ZMQ socket.
        """
        self.subscriber.close()
        self.context.term()
        logger.info("NewsProcessor ZMQ connection closed.")


if __name__ == "__main__":
    # This is for standalone testing of the processor
    processor = NewsProcessor()
    try:
        processor.start_listening()
    except KeyboardInterrupt:
        logger.info("Shutting down NewsProcessor...")
    finally:
        processor.close()
