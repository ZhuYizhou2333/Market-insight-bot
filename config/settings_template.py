# Project settings and configurations
# Telegram Fetcher Configuration
TELEGRAM_CONFIG = {
    "API_ID": "YOUR_API_ID",  # Please replace with your actual API ID
    "API_HASH": "YOUR_API_HASH",  # Please replace with your actual API Hash
    "SESSION_NAME": "telegram_session",
    "CHANNELS": ["some_news_channel"],  # Add target channel usernames here
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
    "CHANNELS": ["trade", "depth"],  # trade, depth, kline_1m, etc.
}

# ZeroMQ Configuration for Market Data
ZMQ_CONFIG.update(
    {
        "MARKET_DATA_PUBLISHER_ADDRESS": "tcp://127.0.0.1:5556",
        "MARKET_DATA_TOPIC_TRADE": "binance_usdm_trade",
        "MARKET_DATA_TOPIC_DEPTH": "binance_usdm_depth",
    }
)
