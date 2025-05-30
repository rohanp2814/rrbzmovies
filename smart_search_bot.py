import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telethon.sync import TelegramClient

API_ID = '26611044'
API_HASH = '9ef2ceed3bd6ac525020d757980f6864'
BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'
CHANNEL_ID = -1002244686281

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tg_client = TelegramClient("anon", API_ID, API_HASH)

NOT_FOUND_LOG = "not_found.log"
RESULTS_PER_PAGE = 5

# Global variables to hold index and titles
video_index = {}
titles = []

def load_index():
    global video_index, titles
    try:
        with open('video_index.json', 'r', encoding='utf-8') as f:
            video_index = json.load(f)
        titles = list(video_index.keys())
        logger.info("Video index reloaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load video index: {e}")

# Load index initially when bot starts
load_index()

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
    if not context.args:
        await update.message.reply_text("Please provide a search query, e.g. /search raid")
        return

    query = " ".join(context.args).strip()
    matches = [(title, video_index[title]) for title in titles if query.lower() in title.lower()]

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

    buttons = [[InlineKeyboardButton(text=title[:60], callback_data=f"movie_{msg_id}")] 
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
        await update_or_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update_or_query.edit_message_text(text, reply_markup=reply_markup)

async def delete_message_after(chat_id: int, message_id: int, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(55 * 60)
    try:
        await context.bot.send_message(chat_id, "⏳ Movie will be deleted in 5 minutes...")
    except Exception as e:
        logger.warning(f"Couldn't send deletion warning: {e}")

    await asyncio.sleep(5 * 60)
    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.warning(f"Couldn't delete movie message: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "next_page":
        context.user_data['page'] += 1
        await send_results(query, context)
        return
    elif data == "prev_page":
        context.user_data['page'] -= 1
        await send_results(query, context)
        return
    elif data == "back_to_results":
        await send_results(query, context)
        return

    if data.startswith("movie_"):
        msg_id = int(data.split("_")[1])

        await query.edit_message_text("🎬 Sending your movie...")
        await tg_client.start()
        try:
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
        context.application.create_task(delete_message_after(sent.chat.id, sent.message_id, context))

        # Show back button
        back_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to results", callback_data="back_to_results")]
        ])
        await query.message.reply_text("🔍 Want to pick another movie?", reply_markup=back_markup)

async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'matches' not in context.user_data:
        await update.message.reply_text("You haven't searched yet. Use /search <query> first.")
        return
    context.user_data['page'] += 1
    await send_results(update, context)

async def prev_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'matches' not in context.user_data:
        await update.message.reply_text("You haven't searched yet. Use /search <query> first.")
        return
    if context.user_data['page'] > 0:
        context.user_data['page'] -= 1
    await send_results(update, context)

async def reloadindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_index()
    await update.message.reply_text("🔄 Video index reloaded successfully!")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sorry, I didn't understand that command.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('search', search_command))
app.add_handler(CommandHandler('reloadindex', reloadindex_command))  # New command added here
app.add_handler(CommandHandler('next', next_command))
app.add_handler(CommandHandler('prev', prev_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.COMMAND, unknown))

print("🤖 Bot is running... Press Ctrl+C to stop.")
app.run_polling()
