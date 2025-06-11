<<<<<<< HEAD
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'

# Handle all messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
        logging.info(f"✅ Channel ID: {chat_id}")
        await message.reply_text(f"Channel ID is: `{chat_id}`", parse_mode="Markdown")
    else:
        await message.reply_text("❗Please forward a message from your private channel.")

# Main entry
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
=======



from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

BOT_TOKEN = '8126440223:AAHg6ML8Ymw3FgAKr1DZAmuFdWfpm_7GBDM'

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id if chat else "Unknown"
    chat_type = chat.type if chat else "Unknown"

    # Safely reply only if message exists
    if update.message:
        await update.message.reply_text(f"Chat ID: {chat_id}\nChat Type: {chat_type}")
    elif update.channel_post:
        await update.channel_post.reply_text(f"Channel Post - Chat ID: {chat_id}")
    else:
        print(f"Received something from chat ID: {chat_id}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, get_chat_id))

    print("Bot is running. Add the bot to a channel or send it a message.")
>>>>>>> 3c966a8 (Reinitialize repository with working bot code)
    app.run_polling()
