import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import Document

api_id = 26611044
api_hash = '9ef2ceed3bd6ac525020f757980f6864'
phone = '+918689887508'

source_channel = -1002244686281
target_channel = -1002544385425

# Session name for storing your login session
session_name = 'session_name'

async def get_media_hash(message):
    media = message.media
    if not media:
        return None
    if hasattr(media, 'document') and isinstance(media.document, Document):
        doc = media.document
        # Unique key for media: document id + access_hash
        return f"{doc.id}_{doc.access_hash}"
    return None

async def load_existing_hashes(client, entity):
    print("Loading existing media hashes from target channel...")
    hashes = set()
    offset_id = 0
    limit = 100
    while True:
        history = await client(GetHistoryRequest(
            peer=entity,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        messages = history.messages
        if not messages:
            break
        for msg in messages:
            media_hash = await get_media_hash(msg)
            if media_hash:
                hashes.add(media_hash)
        offset_id = messages[-1].id
        if len(messages) < limit:
            break
    print(f"Loaded {len(hashes)} existing media hashes.")
    return hashes

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(phone)
    source_entity = await client.get_input_entity(source_channel)
    target_entity = await client.get_input_entity(target_channel)

    existing_hashes = await load_existing_hashes(client, target_entity)

    offset_id = 0
    limit = 50
    total_copied = 0

    while True:
        history = await client(GetHistoryRequest(
            peer=source_entity,
            offset_id=offset_id,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))

        messages = history.messages
        if not messages:
            print("Finished copying all messages.")
            break

        # Process messages in chronological order
        for message in reversed(messages):
            offset_id = message.id
            media_hash = await get_media_hash(message)

            if media_hash and media_hash in existing_hashes:
                print(f"Skipping already copied message ID {message.id}")
                continue

            if message.media:
                try:
                    await client.send_message(target_entity, file=message.media, message=message.message or "")
                    print(f"Copied message ID: {message.id}")
                    total_copied += 1
                    if media_hash:
                        existing_hashes.add(media_hash)
                except Exception as e:
                    print(f"Failed to copy message ID {message.id}: {e}")

    print(f"✅ Finished copying {total_copied} new media messages.")
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
