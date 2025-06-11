from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = 26611044
api_hash = '9ef2ceed3bd6ac525020d757980f6864'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Your session string is:")
    print(client.session.save())
