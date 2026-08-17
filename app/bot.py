"""
Telegram bot entrypoint. Uses polling (no public URL / webhook needed) -
simplest way to run this locally for development and demos.

Deliberately does NOT use slash commands, inline buttons, or menus for the
core experience, per the assignment's "feel conversational, not command-driven"
requirement. /start is the one necessary exception (Telegram's own convention
for initiating a chat with a bot).
"""
import base64
import logging
import os
import tempfile

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

from app.config import TELEGRAM_BOT_TOKEN, validate_config
from app.database import init_db
from app.handlers.onboarding import is_new_user, start_onboarding, is_onboarding_in_progress, handle_onboarding_reply
from app.handlers.conversation import handle_message
from app.llm import transcribe_audio, analyze_image
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
    """Downloads the voice message, transcribes it with Groq Whisper, then
    routes the resulting text through the normal conversation/onboarding flow."""
    chat_id = str(update.effective_chat.id)

    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
    await voice_file.download_to_drive(tmp_path)

    try:
        text = await transcribe_audio(tmp_path)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        await update.message.reply_text("Sorry, I couldn't understand that voice message — could you try typing it instead?")
        return
    finally:
        os.remove(tmp_path)

    if not text or not text.strip():
        await update.message.reply_text("I couldn't catch that — could you try again?")
        return

    if is_new_user(chat_id):
        reply = start_onboarding(chat_id)
    elif is_onboarding_in_progress(chat_id):
        reply = handle_onboarding_reply(chat_id, text)
    else:
        reply = await handle_message(chat_id, text)

    await update.message.reply_text(reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Downloads the largest available photo size, sends it to a Groq vision
    model along with any caption the user included, and replies with the analysis."""
    photo = update.message.photo[-1]  # highest resolution available
    photo_file = await photo.get_file()

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    await photo_file.download_to_drive(tmp_path)

    try:
        with open(tmp_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        caption = update.message.caption or ""
        reply = await analyze_image(image_base64, caption)
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        reply = "Sorry, I had trouble analyzing that image — could you try again?"
    finally:
        os.remove(tmp_path)

    await update.message.reply_text(reply)


async def on_startup(application: Application):
    """
    Runs once the bot's event loop is actually running. The scheduler MUST be
    started from here (not before run_polling()) because AsyncIOScheduler
    needs a running event loop to attach to.
    """
    start_scheduler(application)


def main():
    validate_config()
    init_db()

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Atlas bot starting (polling mode)...")
    application.run_polling()


if __name__ == "__main__":
    main()
