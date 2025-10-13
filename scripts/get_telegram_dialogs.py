"""
Helper script to list all your Telegram dialogs (channels, groups, chats).
This helps you find the correct group ID or entity information.
"""
import asyncio
import os
import sys

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telethon import TelegramClient
from config.settings import TELEGRAM_CONFIG


async def main():
    """List all dialogs and their IDs."""
    os.makedirs(TELEGRAM_CONFIG["SESSION_STORAGE_PATH"], exist_ok=True)
    client = TelegramClient(
        TELEGRAM_CONFIG["SESSION_STORAGE_PATH"] + TELEGRAM_CONFIG["SESSION_NAME"],
        int(TELEGRAM_CONFIG["API_ID"]),
        TELEGRAM_CONFIG["API_HASH"],
    )

    await client.start()
    print("\n=== Your Telegram Dialogs ===\n")

    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        entity_type = type(entity).__name__
        entity_id = entity.id
        entity_title = getattr(entity, "title", None) or getattr(
            entity, "username", "Unknown"
        )

        print(f"Type: {entity_type}")
        print(f"Title: {entity_title}")
        print(f"ID: {entity_id}")

        # For channels/groups, show username if available
        if hasattr(entity, "username") and entity.username:
            print(f"Username: @{entity.username}")

        # For invite-only groups, show access hash
        if hasattr(entity, "access_hash"):
            print(f"Access Hash: {entity.access_hash}")

        print("-" * 50)

    await client.disconnect()
    print("\n=== Done ===")
    print(
        "\nTo use a group/channel in your config, you can use:"
    )
    print("  - Username (e.g., 'channelname' or '@channelname')")
    print("  - Numeric ID (e.g., -1001234567890)")
    print("  - For private groups, use the numeric ID after joining")


if __name__ == "__main__":
    asyncio.run(main())
