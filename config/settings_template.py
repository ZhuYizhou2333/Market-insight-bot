# Project settings and configurations
# Telegram Fetcher Configuration
TELEGRAM_CONFIG = {
    "API_ID": "YOUR_API_ID",  # Please replace with your actual API ID
    "API_HASH": "YOUR_API_HASH",  # Please replace with your actual API Hash
    "SESSION_NAME": "telegram_session",
    "CHANNELS": ["some_news_channel"],  # Add target channel usernames here
        "GROUPS": [
        # Add private group invite hashes or group IDs here
        # For private groups with invite links like t.me/+xxx, add the hash after '+'
        # Or add the numeric group ID after you join
    ],  # Add target group identifiers here
    "SESSION_STORAGE_PATH": "sessions/",
}

# ZeroMQ Configuration
ZMQ_CONFIG = {
    "NEWS_PUBLISHER_ADDRESS": "tcp://127.0.0.1:5555",
    "NEWS_TOPIC": "raw_news",
}

# Binance USD-M Futures Fetcher Configuration
BINANCE_USD_M_FUTURES_CONFIG = {
    "SYMBOLS": ["btcusdt", "ethusdt"],  # Add target symbols here
    "CHANNELS": ["aggTrade", "depth20"],  # trade, depth, kline_1m, etc.
}

# ZeroMQ Configuration for Market Data
ZMQ_CONFIG.update(
    {
        "MARKET_DATA_PUBLISHER_ADDRESS": "tcp://127.0.0.1:5556",
        "MARKET_DATA_TOPIC_TRADE": "binance_usdm_trade",
        "MARKET_DATA_TOPIC_DEPTH": "binance_usdm_depth",
    }
)

# AI Analyzer Configuration
AI_ANALYZER_CONFIG = {
    "MODEL": "qwen-plus-latest",  # 使用的模型
    "MESSAGE_BUFFER_SIZE": 1000,  # 消息缓冲区大小
    "ANALYSIS_INTERVAL": 1000,  # 每 N 条消息进行一次分析（用于波动率等）
    "SUMMARY_MESSAGE_COUNT": 100,  # 摘要使用的消息数量
    "VOLATILITY_MESSAGE_COUNT": 500,  # 波动率分析使用的消息数量
    # 按消息类型的摘要间隔：频道（新闻）每 50 条、社群（群组）每 1000 条
    "SUMMARY_INTERVAL_CHANNEL": 50,
    "SUMMARY_INTERVAL_GROUP": 1000,
}
