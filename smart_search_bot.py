import asyncio
import json
import logging
import os
import re
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from rapidfuzz import process, fuzz
from apscheduler.schedulers.background import BackgroundScheduler
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeVideo

API_ID = 26611044
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
CHANNEL_ID = -1002244686281
SESSION_NAME = 'movie_indexer'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

video_index = {}
titles = []

UNWANTED_PREFIXES = [
    'badshahpiratesofficial', 'mishrimovieshd', 'badshahpiratesoffical',
    'badshahpirates', 'badshah', 'mishrimovies', 'mishri', 'clipmateempire',
    'ap_files', 'runningmovieshd', '@runningmovieshd', 'filmygod', 'hindiwebseries',
    'moviesverse', 'moviezverse', 'sflix', 'primevideo', 'clipmatemovies',
    '@BadshahPiratesOfficial', '@ap_files', '[ap_files]', '[clipmateempire]'
]


def normalize_title(title: str) -> str:
    title = title.lower()
    for prefix in UNWANTED_PREFIXES:
        title = title.replace(prefix.lower(), '')
    title = re.sub(r'\[@[^\]]+\]', '', title)
    title = re.sub(r'\([^)]*\)', '', title)
    title = re.sub(r'[\[\]@_.-]', ' ', title)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[^\w\s]', '', title)
    return title.strip()


def save_index():
    with open("video_index.json", "w", encoding="utf-8") as f:
        json.dump(video_index, f, ensure_ascii=False, indent=2)


def load_index():
    global titles, video_index
    if os.path.exists("video_index.json"):
        with open("video_index.json", encoding="utf-8") as f:
            video_index = json.load(f)
        titles = list(video_index.keys())
        logger.info(f"✅ Loaded {len(titles)} titles from index")


def fetch_videos():
    global video_index, titles
    logger.info("📥 Fetching videos from channel...")
    temp_index = {}
    try:
        with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
            for message in client.iter_messages(CHANNEL_ID):
                if message.video or (message.document and any(
                    isinstance(attr, DocumentAttributeVideo) for attr in message.document.attributes)):
                    title = message.text or message.document.attributes[0].file_name
                    if title:
                        norm_title = normalize_title(title)
                        temp_index[norm_title] = message.video.file_id if message.video else message.document.id
    except Exception as e:
        logger.error(f"Failed to fetch: {e}")
        return
    video_index = temp_index
    titles = list(video_index.keys())
    save_index()
    logger.info(f"📦 Indexed {len(titles)} new videos")


app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🤖 Bot is running."

def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a movie name to search.")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower() if context.args else update.message.text.strip().lower()
    if not query:
        await update.message.reply_text("❌ Please enter a movie name.")
        return

    norm_query = normalize_title(query)

    if norm_query in video_index:
        await update.message.reply_text(f"🎬 Found: {query}\nSending video...")
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_index[norm_query])
        return

    matches = process.extract(norm_query, titles, scorer=fuzz.token_sort_ratio, limit=5)
    matches = [m for m in matches if m[1] > 60]

    if not matches:
        await update.message.reply_text("❌ Movie not found. Try a different name.")
        return

    buttons = [
        [InlineKeyboardButton(text=title, callback_data=f"movie::{title}")]
        for title, score, _ in matches
    ]
    await update.message.reply_text("Did you mean:", reply_markup=InlineKeyboardMarkup(buttons))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("movie::"):
        title = query.data.split("::", 1)[1]
        file_id = video_index.get(title)
        if file_id:
            await query.edit_message_text(f"🎬 Sending: {title}")
            await context.bot.send_video(chat_id=query.message.chat_id, video=file_id)
        else:
            await query.edit_message_text("❌ Video not found.")


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing index...")
    fetch_videos()
    await update.message.reply_text("✅ Refreshed!")


async def main():
    load_index()
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_videos, 'interval', minutes=30)
    scheduler.start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search))

    Thread(target=run_flask, daemon=True).start()
    logger.info("🚀 Bot is running...")
    await app.run_polling()


if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
