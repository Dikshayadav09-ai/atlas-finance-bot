"""
Runs a background job every minute, checks which users' brief_time matches
the current time, and sends them a personalized morning brief for their
watchlist. Stays silent for a user if there's nothing notable to report -
per the assignment's "quality over frequency" principle.
"""
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from app.database import get_session, User
from app.tools.financial_data import get_quote, get_company_news
from app.config import TIMEZONE

logger = logging.getLogger(__name__)


async def _build_brief_for_user(user: User) -> str | None:
    if not user.watchlist_items:
        return None  # nothing to brief on

    sections = []
    for item in user.watchlist_items:
        symbol = item.symbol_or_topic.upper()
        quote = await get_quote(symbol)
        if "error" in quote:
            continue  # skip topics that aren't valid tickers (e.g. "semiconductors")

        change_pct = quote.get("change_percent", "0%").strip("%")
        try:
            is_significant = abs(float(change_pct)) >= 1.0
        except ValueError:
            is_significant = False

        if is_significant:
            sections.append(
                f"• {symbol}: ${quote.get('price')} ({quote.get('change_percent')}) — "
                f"{'up' if float(change_pct) > 0 else 'down'} on the day"
            )

    if not sections:
        return None  # nothing significant - stay silent, per design principle

    return "Morning brief:\n\n" + "\n".join(sections)


async def send_due_briefs(application: Application):
    now_str = datetime.now().strftime("%H:%M")
    session = get_session()
    users = session.query(User).filter_by(onboarding_complete=True, brief_time=now_str).all()
    session.close()

    for user in users:
        brief = await _build_brief_for_user(user)
        if brief:
            try:
                await application.bot.send_message(chat_id=user.telegram_chat_id, text=brief)
            except Exception as e:
                logger.error(f"Failed to send brief to {user.telegram_chat_id}: {e}")


def start_scheduler(application: Application):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_due_briefs, "cron", minute="*", args=[application])
    scheduler.start()
    return scheduler
