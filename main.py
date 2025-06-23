import asyncio
import threading

from communication.zmq_manager import ZMQManager
from data_modules.news import NewsProcessor, TelegramFetcher
from utils.logger import logger


def run_processor(processor: NewsProcessor):
    """Function to run the news processor in a separate thread."""
    try:
        processor.start_listening()
    except Exception as e:
        logger.error(f"NewsProcessor thread encountered an error: {e}")
    finally:
        processor.close()
        logger.info("NewsProcessor thread finished.")


async def main():
    """
    Main entry point for the application.
    Initializes and starts all components.
    """
    logger.info("Intraday Trading Bot Starting...")

    # Initialize ZMQ manager
    zmq_manager = ZMQManager()

    # Initialize and run the NewsProcessor in a separate thread
    news_processor = NewsProcessor()
    processor_thread = threading.Thread(
        target=run_processor, args=(news_processor,), daemon=True
    )
    processor_thread.start()
    logger.info("NewsProcessor started in a background thread.")

    # Initialize and run the TelegramFetcher
    telegram_fetcher = TelegramFetcher(zmq_manager)

    try:
        logger.info("Starting TelegramFetcher...")
        await telegram_fetcher.start()
    except Exception as e:
        logger.error(f"TelegramFetcher encountered an error: {e}")
    finally:
        logger.info("Shutting down application...")
        await telegram_fetcher.stop()
        # The processor thread is a daemon, so it will exit when the main thread exits.
        # The processor's close() method is called within its own thread's finally block.
        zmq_manager.close()
        logger.info("Application has been shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Shutting down.")
