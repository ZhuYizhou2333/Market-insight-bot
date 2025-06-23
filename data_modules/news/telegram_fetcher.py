import json
import os

from telethon import TelegramClient, events

from communication.zmq_manager import ZMQManager
from config.settings import TELEGRAM_CONFIG, ZMQ_CONFIG
from utils.logger import logger


class TelegramFetcher:
    """
    Fetches news from specified Telegram channels and publishes them via ZeroMQ.
    """

    def __init__(self, zmq_manager: ZMQManager):
        """
        Initializes the Telegram client and sets up the ZMQ publisher.

        Args:
            zmq_manager (ZMQManager): An instance of the ZMQManager.
        """
        os.makedirs(TELEGRAM_CONFIG["SESSION_STORAGE_PATH"], exist_ok=True)
        self.client = TelegramClient(
            TELEGRAM_CONFIG["SESSION_STORAGE_PATH"] + TELEGRAM_CONFIG["SESSION_NAME"],
            int(TELEGRAM_CONFIG["API_ID"]),
            TELEGRAM_CONFIG["API_HASH"],
        )
        self.channels = TELEGRAM_CONFIG["CHANNELS"]
        self.zmq_publisher = zmq_manager.get_publisher(
            ZMQ_CONFIG["NEWS_PUBLISHER_ADDRESS"]
        )
        self.news_topic = ZMQ_CONFIG["NEWS_TOPIC"].encode("utf-8")

        # Register the event handler for new messages
        self.client.on(events.NewMessage(chats=self.channels))(self.handle_new_message)
        logger.info("TelegramFetcher initialized and event handler registered.")

    async def handle_new_message(self, event: events.NewMessage.Event):
        """
        Handles new messages from the specified channels.

        Args:
            event (events.NewMessage.Event): The new message event.
        """
        try:
            message_data = {
                "channel": event.chat.username
                if hasattr(event.chat, "username")
                else event.chat.title,
                "message_id": event.message.id,
                "text": event.message.text,
                "date": event.message.date.isoformat(),
            }
            message_json = json.dumps(message_data)

            # Publish the message to ZeroMQ
            self.zmq_publisher.send_multipart(
                [self.news_topic, message_json.encode("utf-8")]
            )
            logger.info(
                f"Published message from {message_data['channel']} to ZMQ topic '{self.news_topic.decode()}'"
            )

        except Exception as e:
            logger.error(f"Error handling new message: {e}")

    async def start(self):
        """
        Starts the Telegram client.
        """
        logger.info("Starting Telegram client...")
        await self.client.start()
        logger.info("Telegram client started.")
        await self.client.run_until_disconnected()

    async def stop(self):
        """
        Stops the Telegram client.
        """
        logger.info("Stopping Telegram client...")
        await self.client.disconnect()
        logger.info("Telegram client stopped.")


if __name__ == "__main__":
    # This is for standalone testing of the fetcher
    import asyncio

    async def main():
        zmq_manager = ZMQManager()
        fetcher = TelegramFetcher(zmq_manager)
        try:
            await fetcher.start()
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            await fetcher.stop()
            zmq_manager.close()

    asyncio.run(main())
