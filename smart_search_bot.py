import json
import logging
import asyncio
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
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

# Normalize titles
def normalize_title(title):
    return re.sub(r'[\W_]+', '', title).lower()

# Load video index
def load_index():
    global video_index, titles
    try:
        with open('video_index.json', 'r', encoding='utf-8') as f:
            video_index = json.load(f)
        titles = list(video_index.keys())
        logger.info(f"Video index loaded with {len(titles)} entries.")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")

# Refresh and update video index from channel
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
                        if hasattr(attr, 'file_name'):
                            filename = attr.file_name
                            break
                if not filename and msg.message:
                    filename = msg.message.strip()[:100]
                if not filename:
                    continue
                norm_title = normalize_title(filename)
                if norm_title not in video_index or video_index[norm_title] != msg.id:
                    video_index[norm_title] = msg.id
                    new_count += 1

        with open("video_index.json", "w", encoding="utf-8") as f:
            json.dump(video_index, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ New entries added: {new_count}")
        return new_count

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Use /search <movie_name> to find movies.")

async def log_not_found(query: str):
    with open(NOT_FOUND_LOG, "a", encoding="utf-8") as f:
        f.write(f"{query}\n")

def get_page(matches, page):
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    return matches[start:end]

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_index()
    if not context.args:
        await update.message.reply_text("Please provide a search query, e.g. /search raid")
        return

    query = " ".join(context.args).strip()
    norm_query = normalize_title(query)
    matches = [(title, video_index[title]) for title in titles if norm_query in normalize_title(title)]
    matches.sort(key=lambda x: x[1], reverse=True)

    if not matches:
        logger.info(f"Search not found: {query}")
        await log_not_found(query)
        await update.message.reply_text("❌ Movie not found. Please check the spelling and try again.")
        return

    context.user_data['matches'] = matches
    context.user_data['page'] = 0
    await send_results(update, context)

async def send_results(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    matches = context.user_data.get('matches', [])
    page = context.user_data.get('page', 0)
    page_matches = get_page(matches, page)

    text = f"🎬 Select a movie (Page {page + 1}):\n\n"
    for title, _ in page_matches:
        text += f"• {title}\n"

    buttons = [[InlineKeyboardButton(text=title[:60], callback_data=f"movie_{msg_id}")] for title, msg_id in page_matches]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="prev_page"))
    if (page + 1) * RESULTS_PER_PAGE < len(matches):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data="next_page"))
    if nav_buttons:
        buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup)

async def delete_message_after(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(55 * 60)
    try:
        await context.bot.send_message(chat_id, "⏳ Movie will be deleted in 5 minutes...")
    except:
        pass
    await asyncio.sleep(5 * 60)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "next_page":
        context.user_data['page'] += 1
        await send_results(query, context)
    elif data == "prev_page":
        context.user_data['page'] -= 1
        await send_results(query, context)
    elif data == "back_to_results":
        await send_results(query, context)
    elif data.startswith("movie_"):
        msg_id = int(data.split("_")[1])
        await query.edit_message_text("🎬 Sending your movie...")
        await tg_client.start()
        try:
            sent = await context.bot.forward_message(
                chat_id=query.message.chat_id,
                from_chat_id=CHANNEL_ID,
                message_id=msg_id
            )
            context.application.create_task(delete_message_after(sent.chat.id, sent.message_id, context))
        except Exception as e:
            await query.message.reply_text(f"⚠️ Couldn't send the movie.\n{e}")
        await tg_client.disconnect()
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to results", callback_data="back_to_results")]
        ])
        await query.message.reply_text("🔍 Want to pick another movie?", reply_markup=back_markup)

# /refresh command
async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing video index. Please wait...")
    count = await fetch_and_update_index()
    load_index()
    await update.message.reply_text(f"✅ Index refreshed! {count} new entries added.")

# Extra commands
async def reloadindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_index()
    await update.message.reply_text("✅ Index reloaded.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

# Run refresh at startup inside bot's event loop
async def on_startup(app):
    logger.info("Starting up: refreshing index...")
    await fetch_and_update_index()
    load_index()
    logger.info("Startup index refresh complete.")

# Initialize the bot
app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()

# Add handlers
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('search', search_command))
app.add_handler(CommandHandler('reloadindex', reloadindex_command))
app.add_handler(CommandHandler('refresh', refresh_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("🤖 Bot is running...")

# Start the bot
app.run_polling()
