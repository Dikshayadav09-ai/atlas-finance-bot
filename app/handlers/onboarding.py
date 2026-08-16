"""
Handles the first-time conversational onboarding.
No forms, no buttons - the bot asks a couple of natural questions and
lets the user skip at any point by just talking normally.

State machine per user (in-memory dict here for simplicity; fine for an
MVP - move to DB-backed state if you need multi-process scaling later).
"""
from app.database import get_session, User, WatchlistItem
from app.config import DEFAULT_BRIEF_TIME

# In-memory onboarding step tracker: {chat_id: step_name}
_onboarding_state: dict[str, str] = {}

WELCOME_MESSAGE = (
    "Hey! I'm Atlas — think of me as a financial analyst who lives in your pocket. "
    "I can research companies, keep an eye on your watchlist, send you a daily brief, "
    "and answer questions the way a colleague would.\n\n"
    "Before we start, quick one: what best describes you — investor, analyst, founder, "
    "student, or something else? (Or just say 'skip' and we'll figure it out as we go.)"
)


def is_new_user(chat_id: str) -> bool:
    session = get_session()
    user = session.query(User).filter_by(telegram_chat_id=chat_id).first()
    session.close()
    return user is None


def start_onboarding(chat_id: str) -> str:
    session = get_session()
    user = User(telegram_chat_id=chat_id, onboarding_complete=False, brief_time=DEFAULT_BRIEF_TIME)
    session.add(user)
    session.commit()
    session.close()

    _onboarding_state[chat_id] = "awaiting_role"
    return WELCOME_MESSAGE


def is_onboarding_in_progress(chat_id: str) -> bool:
    return chat_id in _onboarding_state


def handle_onboarding_reply(chat_id: str, text: str) -> str:
    """Moves the onboarding state machine forward one step at a time."""
    step = _onboarding_state.get(chat_id, "awaiting_role")
    session = get_session()
    user = session.query(User).filter_by(telegram_chat_id=chat_id).first()

    skipped = text.strip().lower() in ("skip", "skip it", "no", "nah")

    if step == "awaiting_role":
        if not skipped:
            user.role = text.strip()
        session.commit()
        _onboarding_state[chat_id] = "awaiting_watchlist"
        reply = (
            "Got it. Are there any companies, sectors, or markets you'd like me to keep "
            "an eye on for you? (e.g. 'AAPL, TSLA, semiconductors' — or say 'skip')"
        )

    elif step == "awaiting_watchlist":
        if not skipped:
            items = [i.strip() for i in text.split(",") if i.strip()]
            for item in items:
                session.add(WatchlistItem(user_id=user.id, symbol_or_topic=item))
            session.commit()
        _onboarding_state[chat_id] = "awaiting_brief_time"
        reply = (
            "Perfect. What time would you like your daily morning brief? "
            "(e.g. '8am' or '08:00' — or say 'skip' for a default of 8:00 AM)"
        )

    elif step == "awaiting_brief_time":
        if not skipped:
            user.brief_time = _normalize_time(text.strip())
        user.onboarding_complete = True
        session.commit()
        del _onboarding_state[chat_id]
        reply = (
            "All set! I'll send your first brief tomorrow morning. In the meantime, "
            "just talk to me like you would a colleague — ask me about a company, "
            "compare two stocks, or upload a report and I'll break it down for you."
        )

    else:
        # Fallback: shouldn't normally happen
        user.onboarding_complete = True
        session.commit()
        del _onboarding_state[chat_id]
        reply = "You're all set — ask me anything, anytime."

    session.close()
    return reply


def _normalize_time(text: str) -> str:
    """Best-effort parse of a casual time string into HH:MM. Falls back to default."""
    text = text.lower().replace(" ", "")
    try:
        if "am" in text or "pm" in text:
            is_pm = "pm" in text
            digits = text.replace("am", "").replace("pm", "")
            hour = int(digits.split(":")[0])
            minute = int(digits.split(":")[1]) if ":" in digits else 0
            if is_pm and hour != 12:
                hour += 12
            if not is_pm and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        elif ":" in text:
            hour, minute = text.split(":")
            return f"{int(hour):02d}:{int(minute):02d}"
    except (ValueError, IndexError):
        pass
    return DEFAULT_BRIEF_TIME
