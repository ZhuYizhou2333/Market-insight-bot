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
    "NEWS_TOPIC": "raw_news"
}