import json
import logging
import asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telethon.sync import TelegramClient

# Telegram API credentials
API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
CHANNEL_ID = -1002244686281
SESSION_NAME = "anon"

# Initialize clients and logging
tg_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOT_FOUND_LOG = "not_found.log"
RESULTS_PER_PAGE = 5
video_index = {}
titles = []

def normalize_title(title):
    return re.sub(r'[\W_]+', '', title).lower()

def load_index():
    global video_index, titles
    try:
        with open('video_index.json', 'r', encoding='utf-8') as f:
            video_index = json.load(f)
        # Sort titles by latest message ID
        titles = sorted(video_index.keys(), key=lambda k: video_index[k], reverse=True)
        logger.info(f"Video index loaded with {len(titles)} entries.")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")

async def fetch_and_update_index():
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        logger.info("Fetching messages from channel...")
        messages = await client.get_messages(CHANNEL_ID, limit=5000)

        try:
            with open("video_index.json", "r", encoding="utf-8") as f:
                video_index = json.load(f)
        except FileNotFoundError:
            video_index = {}

        new_count = 0

        for msg in messages:
            if msg.video or msg.document:
                filename = None
                if msg.document and msg.document.attributes:
                    for attr in msg.document.attributes:
                        if hasattr(attr, 'fi
