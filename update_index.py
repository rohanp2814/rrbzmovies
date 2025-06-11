import asyncio
import json
import re
from telethon.sync import TelegramClient

# Telegram API credentials
API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
CHANNEL_ID = -1002244686281
SESSION_NAME = "anon"



def normalize_filename(name):
    """
    Normalizes the filename by removing unwanted prefixes, extra spaces,
    and non-alphanumeric characters.
    """
   def normalize_title(title):
    unwanted_prefixes = [
        'badshahpiratesofficial',
        'mishrimovieshd',
        'badshahpiratesoffical',
        'badshahpirates',
        'badshah',
        'mishrimovies',
        'mishri',
        'pirates',
        'official',
        'offical'
        'runningmovieshd -'
        'ap_files'
        'runningmovieshd'
        'runningmovieshd_'
    ]
    title = title.lower().strip()
    for prefix in unwanted_prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[^\w\.\-_ ]', '', title)
    return title


async def fetch_and_update_index():
    """
    Fetches messages from the Telegram channel and updates the video index.
    """
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        print("Fetching messages...")
        messages = await client.get_messages(CHANNEL_ID, limit=5000)

        try:
            with open("video_index.json", "r", encoding="utf-8") as f:
                raw_index = json.load(f)
            print(f"Loaded existing index with {len(raw_index)} entries.")
        except FileNotFoundError:
            raw_index = {}
            print("No existing index found. Starting fresh.")

        # Normalize existing keys
        video_index = {normalize_filename(k): v for k, v in raw_index.items()}

        new_count = 0

        for msg in messages:
            print(f"Checking MsgID {msg.id} — Has video: {bool(msg.video)}, Has document: {bool(msg.document)}")

            if msg.video or msg.document:
                filename = None

                # Check document attributes
                if msg.document and msg.document.attributes:
                    for attr in msg.document.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            filename = attr.file_name
                            break

                # Check msg.file.name fallback
                if not filename and hasattr(msg, 'file') and hasattr(msg.file, 'name') and msg.file.name:
                    filename = msg.file.name

                # Fallback to message text
                if not filename and msg.message:
                    filename = msg.message.strip()[:100]

                if not filename:
                    print(f" -> MsgID {msg.id} has no filename or message text, skipping.")
                    continue

                filename_norm = normalize_filename(filename)
                print(f" -> Extracted filename: {filename} (normalized: {filename_norm})")

                if filename_norm not in video_index:
                    video_index[filename_norm] = msg.id
                    new_count += 1
                    print(f" -> New file detected, adding to index: {filename_norm}")
                else:
                    # Update if message id differs
                    if video_index[filename_norm] != msg.id:
                        print(f" -> Filename exists but different message ID, updating.")
                        video_index[filename_norm] = msg.id
                        new_count += 1
                    else:
                        print(f" -> Already in index, skipping.")

        with open("video_index.json", "w", encoding="utf-8") as f:
            json.dump(video_index, f, indent=2, ensure_ascii=False)

        print(f"✅ New entries added: {new_count}")

def log_not_found(query: str):
    """
    Logs search queries that do not yield results into 'not_found.log'.
    """
    with open("not_found.log", "a", encoding="utf-8") as f:
        f.write(f"{query}\n")

if __name__ == "__main__":
    asyncio.run(fetch_and_update_index())
