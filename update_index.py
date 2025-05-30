import json
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaDocument

API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
CHANNEL_ID = -1002244686281
SESSION_NAME = 'anon'

async def update_index():
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        all_messages = []
        offset_id = 0
        limit = 100  # You can adjust batch size

        index = {}

        while True:
            history = await client.get_messages(CHANNEL_ID, limit=limit, offset_id=offset_id)
            if not history:
                break

            for msg in history:
                if msg.media and msg.file:
                    title = msg.file.name or f"file_{msg.id}"
                    index[title] = msg.id
            offset_id = history[-1].id

        with open('video_index.json', 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"Index updated: {len(index)} items")

import asyncio
asyncio.run(update_index())
