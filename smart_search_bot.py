import json 
import logging
import asyncio
import re
from threading import Thread
from difflib import get_close_matches

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
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

tg_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOT_FOUND_LOG = "not_found.log"
RESULTS_PER_PAGE = 5
video_index = {}
titles = []

UNWANTED_PREFIXES = [
    'badshahpiratesofficial', 'mishrimovieshd', 'badshahpiratesoffical',
    'badshahpirates', 'badshah', 'mishrimovies', 'mishri', 'pirates',
    'official', 'offical', 'runningmovieshd', '@RunningMoviesHD'
]

def normalize_title(title):
    title = title.lower().strip()
    for prefix in UNWANTED_PREFIXES:
        if title.startswith(prefix):
            title = title[len(prefix):].strip()
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[^\w\.\-_ ]', '', title)
    return title

def load_index():
    global video_index, titles
    try:
        with open('video_index.json', 'r', encoding='utf-8') as f:
            video_index = json.load(f)
        titles = list(video_index.keys())
        logger.info(f"Video index loaded with {len(titles)} entries.")
    except Exception as e:
        logger.error(f"Failed to load index: {e}")

async def fetch_and_update_index():
    async with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
        logger.info("Fetching messages from channel...")
        messages = await client.get_messages(CHANNEL_ID, limit=5000)
        try:
            with open("video_index.json", "r", encoding="utf-8") as f:
                current_index = json.load(f)
        except FileNotFoundError:
            current_index = {}

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
                if norm_title not in current_index or current_index[norm_title] != msg.id:
                    current_index[norm_title] = msg.id
                    new_count += 1

        with open("video_index.json", "w", encoding="utf-8") as f:
            json.dump(current_index, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ New entries added: {new_count}")
        return new_count

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Use /search <movie_name> to find movies.")

async def log_not_found(query: str):
    with open(NOT_FOUND_LOG, "a", encoding="utf-8") as f:
        f.write(f"{query}
")

def get_page(matches, page):
    start = page * RESULTS_PER_PAGE
    end = start + RESULTS_PER_PAGE
    return matches[start:end]

async def send_typing(context, chat_id):
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

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
        suggestions = get_close_matches(norm_query, titles, n=3, cutoff=0.5)
        suggestion_text = "\n".join(suggestions) if suggestions else "No close matches found."
        await log_not_found(query)
        await update.message.reply_text(
            f"❌ Movie not found.\n
🔍 Suggestions:
{suggestion_text}"
        )
        return

    context.user_data['matches'] = matches
    context.user_data['page'] = 0
    await send_results(update, context)

async def send_results(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    matches = context.user_data.get('matches', [])
    page = context.user_data.get('page', 0)
    page_matches = get_page(matches, page)

    text = f"🎬 Page {page + 1} Results:

"
    for title, _ in page_matches:
        text += f"• {title.title()}
"

    buttons = [[InlineKeyboardButton(f"🎬 {title.title()[:50]}", callback_data=f"movie_{msg_id}")]
               for title, msg_id in page_matches]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data="prev_page"))
    if (page + 1) * RESULTS_PER_PAGE < len(matches):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data="next_page"))
    if nav_buttons:
        buttons.append(nav_buttons)

    reply_markup = InlineKeyboardMarkup(buttons)
    if isinstance(update_or_query, Update):
        await send_typing(context, update_or_query.effective_chat.id)
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

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing video index. Please wait...")
    count = await fetch_and_update_index()
    load_index()
    await update.message.reply_text(f"✅ Index refreshed! {count} new entries added.")

async def reloadindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_index()
    await update.message.reply_text("✅ Index reloaded.")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

async def on_startup(app):
    logger.info("Starting up: refreshing index...")
    await fetch_and_update_index()
    load_index()
    logger.info("Startup index refresh complete.")

flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "Bot is running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('search', search_command))
app.add_handler(CommandHandler('reloadindex', reloadindex_command))
app.add_handler(CommandHandler('refresh', refresh_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("🤖 Bot is running...")

flask_thread = Thread(target=run_flask)
flask_thread.start()
app.run_polling()
