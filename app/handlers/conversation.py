"""
Handles normal (post-onboarding) conversation turns:
- Loads recent history + user context from the DB (this is the assistant's "memory")
- Calls the LLM
- Saves both the user's message and the assistant's reply
"""
from app.database import get_session, User, Message
from app.llm import get_response

HISTORY_LIMIT = 12  # how many recent messages to feed back as context


def _build_user_context(user: User) -> str:
    parts = []
    if user.role:
        parts.append(f"Role: {user.role}")
    if user.watchlist_items:
        symbols = ", ".join(w.symbol_or_topic for w in user.watchlist_items)
        parts.append(f"Watchlist: {symbols}")
    return " | ".join(parts) if parts else ""


async def handle_message(chat_id: str, text: str) -> str:
    session = get_session()
    user = session.query(User).filter_by(telegram_chat_id=chat_id).first()

    if user is None:
        session.close()
        return "Looks like we haven't met yet — send /start or just say hi to get going."

    # Save the incoming user message
    session.add(Message(user_id=user.id, role="user", content=text))
    session.commit()

    # Pull recent history for conversational memory
    recent = (
        session.query(Message)
        .filter_by(user_id=user.id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    recent.reverse()
    history = [{"role": m.role, "content": m.content} for m in recent]

    user_context = _build_user_context(user)
    session.close()

    reply = await get_response(history, user_context=user_context)

    # Save the assistant's reply too, so future turns remember it
    session = get_session()
    session.add(Message(user_id=user.id, role="assistant", content=reply))
    session.commit()
    session.close()

    return reply
