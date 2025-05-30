# indexvideos.py
import json
import asyncio
from telegram.ext import ApplicationBuilder

BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
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

if __name__ == '__main__':
    asyncio.run(index_channel())
