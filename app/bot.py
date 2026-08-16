"""
Telegram bot entrypoint. Uses polling (no public URL / webhook needed) -
simplest way to run this locally for development and demos.

Deliberately does NOT use slash commands, inline buttons, or menus for the
core experience, per the assignment's "feel conversational, not command-driven"
requirement. /start is the one necessary exception (Telegram's own convention
for initiating a chat with a bot).
"""
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

from app.config import TELEGRAM_BOT_TOKEN, validate_config
from app.database import init_db
from app.handlers.onboarding import is_new_user, start_onboarding, is_onboarding_in_progress, handle_onboarding_reply
from app.handlers.conversation import handle_message
from app.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    reply = start_onboarding(chat_id)
    await update.message.reply_text(reply)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text

    if is_new_user(chat_id):
        reply = start_onboarding(chat_id)
    elif is_onboarding_in_progress(chat_id):
        reply = handle_onboarding_reply(chat_id, text)
    else:
        reply = await handle_message(chat_id, text)

    await update.message.reply_text(reply)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder: voice transcription (e.g. via Groq's Whisper endpoint) goes here.
    # Wire this up to download update.message.voice, transcribe it, then pass the
    # resulting text into the same handle_text logic above.
    await update.message.reply_text(
        "Voice message support isn't wired up yet in this starter — but the hook is here "
        "in handle_voice() in app/bot.py, ready for you to add transcription."
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Placeholder: image understanding (charts, screenshots of reports, etc.)
    # goes here - pass the image to a vision-capable model.
    await update.message.reply_text(
        "Image support isn't wired up yet in this starter — the hook is in "
        "handle_photo() in app/bot.py, ready for you to add vision analysis."
    )


def main():
    validate_config()
    init_db()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    start_scheduler(application)

    logger.info("Atlas bot starting (polling mode)...")
    application.run_polling()


if __name__ == "__main__":
    main()
