#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from typing import List, Optional

from binance import AsyncClient, BinanceSocketManager

from communication.zmq_manager import ZMQManager
from config.settings import BINANCE_USD_M_FUTURES_CONFIG, ZMQ_CONFIG
from utils.logger import logger

# 重连配置
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # 秒
MAX_RECONNECT_DELAY = 60  # 最大重连延迟


class BinanceUSDMarginFetcher:
    """
    使用 asyncio 和 Binance 官方 python-binance 库从币安USD-M合约市场获取实时数据,
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

        self.client: Optional[AsyncClient] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self._is_running = False
        self._tasks = []
        logger.info("BinanceUSDMarginFetcher initialized.")

    async def _process_aggTrade_message(self, msg: dict):
        """
        处理聚合交易数据消息。

        Args:
            msg: WebSocket 接收到的消息。
        """
        try:
            if msg.get("e") == "error":
                logger.error(f"WebSocket error: {msg}")
                return

            event_type = msg.get("e")
            if event_type == "aggTrade":
                symbol = msg.get("s", "").lower()
                if symbol:
                    topic = f"{self.trade_topic}.{symbol}"
                    # 包装成与原格式兼容的结构
                    data = {"data": msg}
                    self.zmq_manager.publish_message(self.publisher, topic, data)
        except Exception as e:
            logger.error(f"Error processing aggTrade message: {e}", exc_info=True)

    async def _process_depth_message(self, msg: dict):
        """
        处理深度更新数据消息。

        Args:
            msg: WebSocket 接收到的消息。
        """
        try:
            if msg.get("e") == "error":
                logger.error(f"WebSocket error: {msg}")
                return

            event_type = msg.get("e")
            if event_type == "depthUpdate":
                symbol = msg.get("s", "").lower()
                if symbol:
                    topic = f"{self.depth_topic}.{symbol}"
                    # 包装成与原格式兼容的结构
                    data = {"data": msg}
                    self.zmq_manager.publish_message(self.publisher, topic, data)
        except Exception as e:
            logger.error(f"Error processing depth message: {e}", exc_info=True)

    async def _subscribe_streams(self):
        """
        订阅所有配置的交易对和频道。
        """
        tasks = []

        # 根据配置的 channels 订阅相应的流
        for symbol in self.symbols:
            symbol_lower = symbol.lower()

            for channel in self.channels:
                if channel == "aggTrade":
                    # 订阅聚合交易流
                    logger.info(f"Subscribing to aggTrade stream for {symbol}")
                    ts = self.bsm.aggtrade_futures_socket(symbol_lower)
                    stream_name = f"{symbol}/aggTrade"
                    task = asyncio.create_task(self._handle_socket(ts, self._process_aggTrade_message, stream_name))
                    tasks.append(task)
                elif channel.startswith("depth"):
                    # 订阅深度更新流（支持 depth, depth5, depth10, depth20）
                    logger.info(f"Subscribing to {channel} stream for {symbol}")
                    ds = self.bsm.depth_socket(symbol_lower)
                    stream_name = f"{symbol}/{channel}"
                    task = asyncio.create_task(self._handle_socket(ds, self._process_depth_message, stream_name))
                    tasks.append(task)

        self._tasks = tasks

    async def _handle_socket(self, socket_context, message_handler, stream_name: str):
        """
        处理单个 WebSocket 连接，支持断线重连。

        Args:
            socket_context: BinanceSocketManager 返回的 socket 上下文管理器。
            message_handler: 处理消息的回调函数。
            stream_name: 流的名称，用于日志记录。
        """
        reconnect_attempts = 0

        while self._is_running:
            try:
                async with socket_context as stream:
                    logger.success(f"Connected to {stream_name} stream")
                    reconnect_attempts = 0  # 连接成功后重置重连计数

                    while self._is_running:
                        try:
                            msg = await stream.recv()
                            await message_handler(msg)
                        except asyncio.CancelledError:
                            logger.info(f"Socket handler for {stream_name} cancelled.")
                            raise
                        except Exception as e:
                            logger.error(f"Error processing message from {stream_name}: {e}", exc_info=True)
                            # 消息处理错误，继续接收下一条消息
                            continue

            except asyncio.CancelledError:
                logger.info(f"{stream_name} handler cancelled, exiting.")
                break
            except Exception as e:
                if not self._is_running:
                    break

                reconnect_attempts += 1
                logger.error(f"Connection to {stream_name} lost: {e}")

                if reconnect_attempts > MAX_RECONNECT_ATTEMPTS:
                    logger.error(f"Max reconnection attempts ({MAX_RECONNECT_ATTEMPTS}) reached for {stream_name}. Giving up.")
                    break

                # 指数退避重连
                delay = min(RECONNECT_DELAY * (2 ** (reconnect_attempts - 1)), MAX_RECONNECT_DELAY)
                logger.warning(f"Reconnecting to {stream_name} in {delay} seconds... (attempt {reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS})")
                await asyncio.sleep(delay)

    async def start(self) -> None:
        """
        使用 asyncio 启动 WebSocket 数据获取。
        """
        if self._is_running:
            logger.warning("BinanceUSDMarginFetcher is already running.")
            return

        logger.info("Starting BinanceUSDMarginFetcher...")
        self._is_running = True

        # 初始化 Binance 异步客户端（用于期货）
        self.client = await AsyncClient.create()
        self.bsm = BinanceSocketManager(self.client, user_timeout=60)

        # 订阅所有流
        await self._subscribe_streams()

        # 等待所有任务完成
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            logger.info("All socket tasks cancelled.")

        logger.info("BinanceUSDMarginFetcher run loop finished.")

    async def stop(self):
        """停止所有数据获取活动。"""
        if not self._is_running:
            return
        logger.info("Stopping Binance USD-M Futures Fetcher...")
        self._is_running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()

        # 等待所有任务结束
        await asyncio.gather(*self._tasks, return_exceptions=True)

        # 关闭客户端
        if self.client:
            await self.client.close_connection()

        logger.success("Binance USD-M Futures Fetcher stopped.")
