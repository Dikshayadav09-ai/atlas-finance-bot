"""
SQLite database setup using SQLAlchemy ORM.
Stores: users, their preferences, watchlist items, and conversation history.
This is what gives the assistant "memory" across sessions.
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_chat_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    role = Column(String, nullable=True)  # investor / analyst / student / etc.
    onboarding_complete = Column(Boolean, default=False)
    brief_time = Column(String, default="08:00")  # HH:MM, when to send daily brief
    created_at = Column(DateTime, default=datetime.utcnow)

    watchlist_items = relationship("WatchlistItem", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol_or_topic = Column(String, nullable=False)  # e.g. "AAPL" or "semiconductors"
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="watchlist_items")


class Message(Base):
    """Stores conversation history so the assistant has context across turns."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="messages")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
