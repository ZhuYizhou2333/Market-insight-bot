import asyncio

from communication.zmq_manager import ZMQManager
from data_modules.market_data.binance_fetcher import BinanceUSDMarginFetcher
from data_modules.market_data.processor import MarketDataProcessor
from data_modules.news import NewsProcessor, TelegramFetcher
from utils.logger import logger


async def main():
    """
    Main entry point for the application.
    Initializes and starts all components, ensuring graceful shutdown.
    """
    logger.info("Intraday Trading Bot Starting...")

    zmq_manager = ZMQManager()
    telegram_fetcher = TelegramFetcher(zmq_manager)
    binance_fetcher = BinanceUSDMarginFetcher(zmq_manager)
    news_processor = NewsProcessor(zmq_manager)
    market_data_processor = MarketDataProcessor(zmq_manager)

    fetcher_tasks = []
    try:
        # 1. Start processors to listen for data
        logger.info("Starting data processors...")
        news_processor.start_listening()
        market_data_processor.start_listening()
        logger.success("Data processors started.")

        # 2. Start long-running fetcher tasks to publish data
        logger.info("Starting data fetching loops...")

        fetcher_tasks.append(asyncio.create_task(binance_fetcher.start()))
        fetcher_tasks.append(asyncio.create_task(telegram_fetcher.start()))

        # Wait for all fetcher tasks to complete (they will run indefinitely)
        await asyncio.gather(*fetcher_tasks)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in the main loop: {e}", exc_info=True
        )
    finally:
        logger.info("Shutting down application...")

        # 1. Stop fetchers to prevent new data from being published
        logger.info("Stopping data fetchers...")
        # The stop methods should be idempotent and handle being called
        # even if the fetcher failed to start.
        await telegram_fetcher.stop()
        await binance_fetcher.stop()

        # 2. Stop processors
        logger.info("Stopping data processors...")
        news_processor.stop_listening()
        market_data_processor.stop_listening()

        # 3. Close ZMQ manager
        logger.info("Closing ZMQ manager...")
        zmq_manager.close()

        logger.success("Application has been shut down gracefully.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user. Shutting down.")
