# movie_search_bot.py
import json
import logging
from textblob import TextBlob
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
INDEX_FILE = 'videos.json'

logging.basicConfig(level=logging.INFO)

def load_index():
    try:
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if not query:
        await update.message.reply_text("❗Please send a movie name.")
        return

    corrected = str(TextBlob(query).correct())
    logging.info(f"User query: {query} → Corrected: {corrected}")
    await update.message.reply_text(f"🔍 Searching for: `{corrected}`", parse_mode='Markdown')

    # Search local index
    index = load_index()
    for entry in index:
        if corrected.lower() in entry['caption'].lower():
            await update.message.reply_video(
                video=entry['file_id'],
                caption=entry['caption']
            )
            return

    await update.message.reply_text("🚫 Movie not found.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
