import json
import logging
import asyncio
from datetime import timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telethon.sync import TelegramClient
from telethon.tl.types import PeerChannel

API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
CHANNEL_ID = -1002244686281

# Load index
with open('video_index.json', 'r', encoding='utf-8') as f:
    video_index = json.load(f)

titles = list(video_index.keys())
id_map = video_index

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tg_client = TelegramClient("anon", API_ID, API_HASH)

# File to log not found searches
NOT_FOUND_LOG = "not_found.log"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Use /search <movie_name> to find movies.")

async def log_not_found(query: str):
    with open(NOT_FOUND_LOG, "a", encoding="utf-8") as f:
        f.write(f"{query}\n")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a search query, e.g. /search raid")
        return

    query = " ".join(context.args).strip()
    matches = [(title, id_map[title]) for title in titles if query.lower() in title.lower()][:15]

    if not matches:
        logger.info(f"Search not found: {query}")
        await log_not_found(query)
        await update.message.reply_text("❌ Movie not found. Please check the spelling and try again.")
        return

    buttons = [
        [InlineKeyboardButton(text=title, callback_data=str(msg_id))]
        for title, msg_id in matches
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎬 Select a movie:", reply_markup=reply_markup)

async def delete_message_after(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    # Send warning 5 minutes before deletion
    await asyncio.sleep(55 * 60)  # wait 55 minutes
    try:
        await context.bot.send_message(chat_id, "⏳ Movie will be deleted in 5 minutes...")
    except Exception as e:
        logger.warning(f"Couldn't send deletion warning: {e}")

    await asyncio.sleep(5 * 60)  # wait 5 minutes more (total 60)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.warning(f"Couldn't delete movie message: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    msg_id = int(query.data)  # callback_data sent as string

    await query.edit_message_text("🎬 Sending your movie...")

    await tg_client.start()
    try:
        # Forward the movie message and get the sent message
        sent = await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
    except Exception as e:
        await query.message.reply_text(f"⚠️ Couldn't send the movie.\n{e}")
        await tg_client.disconnect()
        return

    await tg_client.disconnect()

    # Schedule deletion of the forwarded movie message after 1 hour with warning
    context.application.create_task(delete_message_after(sent.chat.id, sent.message_id, context))

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('search', search_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("🤖 Bot is running... Press Ctrl+C to stop.")
app.run_polling()
