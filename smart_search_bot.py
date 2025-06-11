import os, json, logging, asyncio, re
from threading import Thread
from flask import Flask
from rapidfuzz import process, fuzz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from session_string import SESSION

API_ID = 26611044
API_HASH = "9ef2ceed3bd6ac525020d757980f6864"
BOT_TOKEN = "8126440223:AAHrzJZ_ymHplsQ3n99kJH09UQjuq1n6UP4"
CHANNEL_ID = -1002244686281
ADMIN_ID = 1162354049

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
tg_client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

video_index = {}
titles = []
RESULTS_PER_PAGE = 5
UNWANTED_PREFIXES = [
    'badshahpiratesofficial', 'mishrimovieshd', 'badshahpiratesoffical',
    'badshahpirates', 'badshah', 'mishrimovies', 'mishri',
    'clipmateempire', 'ap_files', 'runningmovieshd', 'filmygod',
    'hindiwebseries', 'moviesverse', 'moviezverse', 'sflix',
    'primevideo', 'clipmatemovies'
]

def normalize_title(t):
    t = t.lower()
    t = re.sub(r'[@\[\](){}<>._\-]', ' ', t)
    for pref in UNWANTED_PREFIXES:
        t = re.sub(re.escape(pref), ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def load_index():
    global video_index, titles
    try:
        with open("video_index.json", "r", encoding="utf-8") as f:
            video_index = json.load(f)
        titles[:] = list(video_index.keys())
        logger.info(f"✅ Loaded {len(titles)} titles")
    except FileNotFoundError:
        video_index.clear()
        titles.clear()

async def fetch_and_update_index():
    await tg_client.connect()
    messages = await tg_client.get_messages(CHANNEL_ID, limit=15000)
    current = {}
    added = 0
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
            norm = normalize_title(filename)
            if norm and norm not in current:
                current[norm] = msg.id
                added += 1
    with open("video_index.json", "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2, ensure_ascii=False)
    await tg_client.disconnect()
    logger.info(f"📦 Indexed {added} new videos")
    return added

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to MovieBot!*

"
        "🎬 Use /search <movie name> to find your favorite films
"
        "🔄 Use /refresh to sync latest uploads",
        parse_mode="Markdown"
    )

async def search(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        return await update.message.reply_text("❗ Use: /search <movie name>")
    q = normalize_title(" ".join(ctx.args))
    results = process.extract(q, titles, scorer=fuzz.token_set_ratio, limit=20)
    matches = [(title, video_index[title]) for title, score, _ in results if score > 55]
    if not matches:
        return await update.message.reply_text("❌ No matches found.")
    ctx.user_data["matches"], ctx.user_data["page"] = matches, 0
    await show_page(update, ctx)

async def show_page(update_or_cb, ctx):
    matches = ctx.user_data["matches"]
    page = ctx.user_data.get("page", 0)
    total = (len(matches) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
    items = matches[page*RESULTS_PER_PAGE:(page+1)*RESULTS_PER_PAGE]
    buttons = [[InlineKeyboardButton(f"🎬 {t[:50]}", callback_data=f"movie_{mid}")] for t, mid in items]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("👈 Previous", callback_data="prev"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("Next 👉", callback_data="next"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("🚀 Jump to Page", callback_data="jump")])
    kb = InlineKeyboardMarkup(buttons)
    msg = f"🎯 Top Matches (Page {page+1}/{total})"
    if isinstance(update_or_cb, Update):
        await update_or_cb.message.reply_text(msg, reply_markup=kb)
    else:
        await update_or_cb.edit_message_text(msg, reply_markup=kb)

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cb = update.callback_query
    await cb.answer()
    data = cb.data
    if data.startswith("movie_"):
        msg_id = int(data.split("_")[1])
        await cb.edit_message_text("📤 Sending movie... Please wait")
        await tg_client.start()
        try:
            await ctx.bot.forward_message(cb.message.chat.id, CHANNEL_ID, msg_id)
        except Exception as e:
            return await cb.message.reply_text(f"⚠️ {e}")
        await tg_client.disconnect()
        return await cb.message.reply_text("✅ Sent. Back?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return to List", callback_data="back")]]))

    page = ctx.user_data.get("page", 0)
    if data == "next":
        ctx.user_data["page"] = page + 1
    elif data == "prev":
        ctx.user_data["page"] = max(0, page - 1)
    elif data == "jump":
        ctx.user_data["await_jump"] = True
        return await cb.edit_message_text("🚀 Send page number:")
    elif data == "back":
        return await show_page(cb, ctx)

    await show_page(cb, ctx)

async def jump(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.user_data.get("await_jump"):
        return
    ctx.user_data["await_jump"] = False
    try:
        num = int(update.message.text.strip()) - 1
        total = (len(ctx.user_data["matches"]) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE
        if 0 <= num < total:
            ctx.user_data["page"] = num
            return await show_page(update, ctx)
        await update.message.reply_text(f"❗ Enter between 1 and {total}")
    except:
        await update.message.reply_text("❗ Invalid number.")

async def refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Updating index... Please wait")
    added = await fetch_and_update_index()
    load_index()
    await update.message.reply_text(f"✅ Index refreshed. Added {added} new videos.")

async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("⛔ Unauthorized")
    for fn in ("anon.session-journal", "video_index.json"):
        try:
            os.remove(fn)
        except:
            pass
    await update.message.reply_text("🧹 Cleaned. Redeploy to re-auth.")

async def reload_index(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    load_index()
    await update.message.reply_text("🔁 Index reloaded from disk.")

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Try /search or /refresh")

flask = Flask("")

@flask.route("/")
def home():
    return "🤖 Bot running"

def run_flask():
    flask.run("0.0.0.0", 8080)

async def on_startup(app):
    await tg_client.connect()
    me = await tg_client.get_me()
    print(f"✅ Logged in as: {me.username or me.first_name}")
    if not os.path.exists("video_index.json"):
        await fetch_and_update_index()
    load_index()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("reloadindex", reload_index))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), jump))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    Thread(target=run_flask).start()
    app.run_polling()

if __name__ == "__main__":
    main()
