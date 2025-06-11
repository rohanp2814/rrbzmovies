<<<<<<< HEAD
# indexvideos.py
import json
import asyncio
from telegram.ext import ApplicationBuilder

BOT_TOKEN = '8126440223:AAHrzJZ_ymHplsQ3n99kJH09UQjuq1n6UP4'
CHANNEL_ID = -1002244686281
INDEX_FILE = 'videos.json'

async def index_channel():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot = app.bot

    # ✅ Await get_chat to get the actual chat object
    chat = await bot.get_chat(CHANNEL_ID)

    messages = []
    async for message in bot.get_chat_history(chat_id=CHANNEL_ID, limit=100):
        if message.video:
            messages.append({
                'file_id': message.video.file_id,
                'caption': message.caption or '',
            })

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)

    print(f"✅ Indexed {len(messages)} videos.")
=======
# indexvideos.py (fixed for channel ID)
import asyncio
import json
import re
from telethon.sync import TelegramClient
from telethon.tl.types import Message

api_id = 26611044 # 🔁 Replace with your actual API ID
api_hash = '9ef2ceed3bd6ac525020d757980f6864'  # 🔁 Replace with your actual API Hash
channel_id = -1002244686281  # ✅ Your actual private channel ID
INDEX_FILE = 'videos.json'

def clean_title(title):
    if not title:
        return ""

    # Remove markdown (**bold**, etc.)
    title = re.sub(r"\*+", "", title)

    # Remove Telegram handles and unwanted prefixes
    unwanted_patterns = [
        r'^\s*\[?@?badshahpiratesofficial\]?\s*',
        r'^\s*\[?@?runningmovieshd\]?\s*',
        r'^\s*\[?@?ap_files\]?\s*',
        r'^\s*\[?@?clipmateempire\]?\s*',
        r'^\s*\[?@?.*?movies\]?\s*',
        r'^\s*forwarded\sfrom.*',
        r'[-_]+',
    ]

    title = title.strip().lower()

    for pattern in unwanted_patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    # Normalize whitespace and remove extra characters
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r"[^\w\s().-]", "", title)  # remove extra symbols
    title = title.strip()

    return title

async def index_channel():
    client = TelegramClient('indexsession', api_id, api_hash)
    await client.start()

    print("🔍 Resolving channel...")
    entity = await client.get_entity(channel_id)

    print("📥 Indexing messages...")
    videos = []
    async for message in client.iter_messages(entity):
        if isinstance(message, Message):
            if message.video or (
                message.document and 
                message.document.mime_type and 
                message.document.mime_type.startswith("video/")
            ):
                videos.append({
                    'file_id': message.file.id,
                    'title': clean_title(message.text or '')
                })

                if len(videos) % 500 == 0:
                    print(f"✅ Indexed {len(videos)} videos...")

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"🎉 Done! Total indexed videos: {len(videos)}")

>>>>>>> 3c966a8 (Reinitialize repository with working bot code)

if __name__ == '__main__':
    asyncio.run(index_channel())
