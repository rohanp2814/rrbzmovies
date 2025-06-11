from telethon.sync import TelegramClient
<<<<<<< HEAD
import asyncio
import json

# Your Telegram API credentials
API_ID = 26611044  # <-- replace with your actual API ID
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'  # <-- replace with your actual API HASH

CHANNEL_ID = -1002244686281  # Your private channel ID

# Index dictionary to store titles and message IDs
index = {}

async def main():
    async with TelegramClient('user_session', API_ID, API_HASH) as client:
        me = await client.get_me()
        print(f"Signed in successfully as {me.first_name} {me.last_name or ''}")

        async for message in client.iter_messages(CHANNEL_ID):
            if message.video and message.text:
                index[message.text] = message.id

        # Save the index to a JSON file
        with open("video_index.json", "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"✅ Indexed {len(index)} video messages and saved to video_index.json.")

# Run it
=======
from telethon.tl.types import Document
import asyncio
import json
import re

API_ID = 26611044
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
CHANNEL_ID = -1002244686281  # Replace with your real channel ID or @username

INDEX_FILE = "video_index.json"

def clean_title(title):
    if not title:
        return ""
    title = re.sub(r"\*+", "", title)  # Remove bold formatting
    unwanted_patterns = [
        r'^\s*\[?@?badshahpiratesofficial\]?\s*',
        r'^\s*\[?@?runningmovieshd\]?\s*',
        r'^\s*\[?@?ap_files\]?\s*',
        r'^\s*\[?@?clipmateempire\]?\s*',
        r'^\s*forwarded\sfrom.*',
        r'[-_]+',
    ]
    title = title.strip().lower()
    for pattern in unwanted_patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[^\w\s().-]", "", title)
    return title.strip()

async def main():
    index = []
    async with TelegramClient('user_session', API_ID, API_HASH) as client:
        me = await client.get_me()
        print(f"✅ Logged in as {me.first_name} {me.last_name or ''}")

        async for message in client.iter_messages(CHANNEL_ID):
            if message.video or (
                message.document and message.document.mime_type and message.document.mime_type.startswith("video/")
            ):
                raw_title = message.text or message.message or ""
                cleaned = clean_title(raw_title)
                if not cleaned:
                    continue
                index.append({
                    "title": cleaned,
                    "file_id": message.file.id,
                    "message_id": message.id
                })

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        print(f"✅ Indexed {len(index)} videos and saved to {INDEX_FILE}.")

# Run the script
>>>>>>> 3c966a8 (Reinitialize repository with working bot code)
asyncio.run(main())
