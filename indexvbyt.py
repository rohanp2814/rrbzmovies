from telethon.sync import TelegramClient
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
asyncio.run(main())
