import asyncio
import json
import logging
import re
import nest_asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from rapidfuzz import process, fuzz

# Apply nest_asyncio patch early to support nested event loops
nest_asyncio.apply()

API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
CHANNEL_ID = -1002244686281  # Your channel ID (make sure this is an int)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UNWANTED_PREFIXES = [
    'badshahpiratesofficial', 'mishrimovieshd', 'badshahpiratesoffical',
    'badshahpirates', 'badshah', 'mishrimovies', 'mishri', 'clipmateempire',
    'ap_files', 'runningmovieshd', '@runningmovieshd', 'filmygod', 'hindiwebseries',
    'moviesverse', 'moviezverse', 'sflix', 'primevideo', 'clipmatemovies',
    '@BadshahPiratesOfficial', '@ap_files', '[ap_files]', '[clipmateempire]'
]

video_index = {}
titles = []

def normalize_title(title: str) -> str:
    # Lowercase, remove unwanted patterns and prefixes, clean spacing and punctuation
    title = title.lower()
    title = re.sub(r'\[@[^]]+\]', '', title)  # Remove [@something]
    title = re.sub(r'\([^)]*\)', '', title)  # Remove (anything)
    title = re.sub(r'[\[\]@_.-]', ' ', title)  # Replace these chars with space
    for prefix in UNWANTED_PREFIXES:
        title = re.sub(re.escape(prefix), '', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+', ' ', title)  # Collapse multiple spaces
    title = re.sub(r'[^\w\s]', '', title)  # Remove punctuation except space
    return title.strip()

def load_index():
    global video_index, titles
    try:
        with open('video_index.json', 'r', encoding='utf-8') as f:
            video_index = json.load(f)
        titles = list(video_index.keys())
        logger.info(f"✅ Loaded {len(titles)} titles from index")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        video_index = {}
        titles = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send me a movie name to search.")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).strip().lower() if context.args else update.message.text.strip().lower()
    if not query:
        await update.message.reply_text("Please enter a movie name to search.")
        return

    normalized_query = normalize_title(query)
    logger.info(f"Searching for: {normalized_query}")

    # Exact match
    if normalized_query in video_index:
        file_id = video_index[normalized_query]
        await update.message.reply_text(f"Found: {query}\nSending video...")
        await context.bot.send_video(chat_id=update.effective_chat.id, video=file_id)
        return

    # Fuzzy match suggestions
    matches = process.extract(normalized_query, titles, scorer=fuzz.token_sort_ratio, limit=5)
    matches = [m for m in matches if m[1] > 60]  # Filter low similarity matches

    if not matches:
        await update.message.reply_text("❌ Movie not found and no suggestions available.")
        return

    buttons = [
        [InlineKeyboardButton(text=title, callback_data=f"movie::{title}")]
        for title, score, _ in matches
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Did you mean:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("movie::"):
        selected_title = data.split("::", 1)[1]
        file_id = video_index.get(selected_title)
        if file_id:
            await query.edit_message_text(f"Sending movie: {selected_title}")
            await context.bot.send_video(chat_id=query.message.chat_id, video=file_id)
        else:
            await query.edit_message_text("❌ Video file not found for this selection.")

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder to reindex from your channel, here just reload from file
    await update.message.reply_text("🔄 Refreshing movie index...")
    load_index()
    await update.message.reply_text("✅ Index refreshed!")

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🤖 Bot is running."

def run_flask():
    # Run Flask in a thread so it won't block asyncio event loop
    flask_app.run(host="0.0.0.0", port=8080)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("refresh", refresh_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), search))

    Thread(target=run_flask, daemon=True).start()

    load_index()

    logger.info("Bot polling started")
    await app.run_polling()

if __name__ == "__main__":
    import sys
    import asyncio

    # This works well on Windows for Telegram bot + Flask
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
