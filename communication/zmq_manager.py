import json
from typing import Any, List, Tuple

import zmq

from utils.logger import logger


class ZMQManager:
    """
    Manages ZeroMQ connections for publishing and subscribing to topics.
    Handles message serialization (JSON) and deserialization.
    """

    def __init__(self):
        """
        Initializes the ZMQ context and socket lists.
        """
        self.context = zmq.Context()
        self.publishers = {}
        self.subscribers = []
        logger.info("ZMQManager initialized.")

    def get_publisher(self, address: str) -> zmq.Socket:
        """
        Creates and returns a ZMQ publisher socket for the given address.
        If a publisher for this address already exists, it returns the existing one.

        Args:
            address: The address to bind the publisher to (e.g., "tcp://*:5555").

        Returns:
            The ZMQ publisher socket.
        """
        if address not in self.publishers:
            try:
                publisher = self.context.socket(zmq.PUB)
                publisher.bind(address)
                self.publishers[address] = publisher
                logger.info(f"ZMQ Publisher bound to {address}")
            except zmq.ZMQError as e:
                logger.error(f"Failed to bind ZMQ publisher to {address}: {e}")
                raise
        return self.publishers[address]

    def get_subscriber(self, address: str, topics: List[str]) -> zmq.Socket:
        """
        Creates and returns a ZMQ subscriber socket.

        Args:
            address: The address to connect the subscriber to (e.g., "tcp://localhost:5555").
            topics: A list of topics to subscribe to.

        Returns:
            The ZMQ subscriber socket.
        """
        try:
            subscriber = self.context.socket(zmq.SUB)
            subscriber.connect(address)
            for topic in topics:
                subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
            self.subscribers.append(subscriber)
            logger.info(f"ZMQ Subscriber connected to {address} for topics: {topics}")
            return subscriber
        except zmq.ZMQError as e:
            logger.error(f"Failed to connect ZMQ subscriber to {address}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while creating ZMQ subscriber: {e}")
            raise

    def publish_message(self, publisher_socket: zmq.Socket, topic: str, message: Any):
        """
        Publishes a message to a given topic. Serializes message to JSON.

        Args:
            publisher_socket: The publisher socket to use.
            topic: The message topic.
            message: The message payload (should be JSON-serializable).
        """
        try:
            message_json = json.dumps(message).encode("utf-8")
            publisher_socket.send_multipart([topic.encode("utf-8"), message_json])
            # logger.info(f"Published message to topic '{topic}': {message}")
        except Exception as e:
            logger.error(f"Failed to publish message to topic '{topic}': {e}")

    def receive_message(
        self, subscriber_socket: zmq.Socket, flags: int = 0
    ) -> Tuple[str, Any] | None:
        """
        Receives a multipart message and deserializes it from JSON.

        Args:
            subscriber_socket: The subscriber socket to receive from.
            flags: ZMQ flags to use for receiving (e.g., zmq.NOBLOCK).

        Returns:
            A tuple containing the topic and message, or None if no message
            is received immediately when using zmq.NOBLOCK.
        """
        try:
            topic_bytes, message_bytes = subscriber_socket.recv_multipart(flags=flags)
            topic = topic_bytes.decode("utf-8")
            message = json.loads(message_bytes.decode("utf-8"))
            return topic, message
        except zmq.Again:
            # This exception is expected when using zmq.NOBLOCK and no message is available.
            return None

    def close(self):
        """
        Closes all ZMQ sockets and terminates the context.
        """
        for pub in self.publishers.values():
            pub.close()
        for sub in self.subscribers:
            sub.close()
        self.context.term()
        logger.info("ZMQ context and all sockets terminated.")
