#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import List

from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager

from communication.zmq_manager import ZMQManager
from config.settings import BINANCE_USD_M_FUTURES_CONFIG, ZMQ_CONFIG
from utils.logger import logger


class BinanceUSDMarginFetcher:
    """
    使用 asyncio 和 unicorn-binance-websocket-api 从币安USD-M合约市场获取实时数据，
    并通过 ZeroMQ 进行发布。
    """

    def __init__(self, zmq_manager: ZMQManager):
        """
        初始化 BinanceUSDMarginFetcher.

        Args:
            zmq_manager: 用于发布数据的 ZMQManager 实例。
        """
        self.zmq_manager = zmq_manager
        self.symbols: List[str] = BINANCE_USD_M_FUTURES_CONFIG["SYMBOLS"]
        self.channels: List[str] = BINANCE_USD_M_FUTURES_CONFIG["CHANNELS"]
        self.trade_topic: str = ZMQ_CONFIG["MARKET_DATA_TOPIC_TRADE"]
        self.depth_topic: str = ZMQ_CONFIG["MARKET_DATA_TOPIC_DEPTH"]

        self.publisher = self.zmq_manager.get_publisher(
            ZMQ_CONFIG["MARKET_DATA_PUBLISHER_ADDRESS"]
        )

        self.ubwa = BinanceWebSocketApiManager(
            exchange="binance.com-futures",
            output_default="dict",  # 直接输出字典，无需手动json.loads
            enable_stream_signal_buffer=True,  # 启用信号缓冲
            process_stream_signals=self._receive_stream_signal,
        )
        self._is_running = False
        logger.info("BinanceUSDMarginFetcher initialized.")

    async def _process_stream_data(self, stream_id: int) -> None:
        """
        异步处理从WebSocket队列中接收到的数据。
        这是一个回调函数，由 `create_stream` 的 `process_asyncio_queue` 参数指定。

        Args:
            stream_id: 数据流的ID。
        """
        stream_label = self.ubwa.get_stream_label(stream_id)
        logger.info(f"Starting data processing for stream: {stream_label}")
        while self._is_running and not self.ubwa.is_stop_request(stream_id):
            try:
                data = await self.ubwa.get_stream_data_from_asyncio_queue(stream_id)

                event_type = data.get("data", {}).get("e")
                if not event_type:
                    logger.warning(f"Event type not found in stream data: {data}")
                    continue

                symbol = data.get("data", {}).get("s", "").lower()
                if not symbol:
                    logger.warning(f"Symbol not found in stream data: {data}")
                    continue

                if event_type == "trade":
                    topic = f"{self.trade_topic}.{symbol}"
                    self.zmq_manager.publish_message(self.publisher, topic, data)
                elif event_type == "depthUpdate":
                    topic = f"{self.depth_topic}.{symbol}"
                    self.zmq_manager.publish_message(self.publisher, topic, data)

            except asyncio.CancelledError:
                logger.info(f"Processing task for stream '{stream_label}' cancelled.")
                break
            except Exception as e:
                logger.error(
                    f"Error processing stream data for '{stream_label}': {e}",
                    exc_info=True,
                )
            finally:
                # 确认任务完成，以便队列可以移除该项
                self.ubwa.asyncio_queue_task_done(stream_id)

    def _receive_stream_signal(
        self, signal_type=None, stream_id=None, data_record=None, error_msg=None
    ) -> None:
        """
        处理来自 WebSocket 管理器的信号，用于日志记录和监控。
        """
        stream_label = self.ubwa.get_stream_label(stream_id=stream_id) or "manager"
        logger.info(
            f"Received stream signal for '{stream_label}': "
            f"Type={signal_type}, Data={data_record}, Error={error_msg}"
        )

    async def start(self) -> None:
        """
        使用 asyncio 启动 WebSocket 数据获取。
        """
        if self._is_running:
            logger.warning("BinanceUSDMarginFetcher is already running.")
            return

        logger.info("Starting BinanceUSDMarginFetcher...")
        self._is_running = True

        self.ubwa.create_stream(
            channels=self.channels,
            markets=self.symbols,
            process_asyncio_queue=self._process_stream_data,
            stream_label="usd_m_futures_data",
        )

        # 保持运行并监控状态
        while self._is_running and not self.ubwa.is_manager_stopping():
            await asyncio.sleep(1)

        logger.info("BinanceUSDMarginFetcher run loop finished.")

    async def stop(self):
        """停止所有数据获取活动。"""
        if not self._is_running:
            return
        logger.info("Stopping Binance USD-M Futures Fetcher...")
        self._is_running = False

        # This gracefully stops all streams and the manager.
        # The `_process_stream_data` and `start` loops will terminate
        # because `_is_running` is now False.
        self.ubwa.stop_manager_with_all_streams()

        # Give a moment for the library to clean up its tasks.
        await asyncio.sleep(2)
        logger.success("Binance USD-M Futures Fetcher stopped.")
