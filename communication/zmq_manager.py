import zmq

from utils.logger import logger


class ZMQManager:
    """
    Manages ZeroMQ connections for publishing and subscribing to topics.
    """

    def __init__(self):
        """
        Initializes the ZMQ context.
        """
        self.context = zmq.Context()
        self.publisher = None

    def get_publisher(self, address: str):
        """
        Creates and returns a ZMQ publisher socket.

        Args:
            address (str): The address to bind the publisher to.

        Returns:
            zmq.Socket: The ZMQ publisher socket.
        """
        if not self.publisher:
            try:
                self.publisher = self.context.socket(zmq.PUB)
                self.publisher.bind(address)
                logger.info(f"ZMQ Publisher bound to {address}")
            except zmq.ZMQError as e:
                logger.error(f"Failed to bind ZMQ publisher to {address}: {e}")
                raise
        return self.publisher

    def close(self):
        """
        Closes all ZMQ sockets and terminates the context.
        """
        if self.publisher:
            self.publisher.close()
        self.context.term()
        logger.info("ZMQ context terminated.")
