"""
Loads all configuration from environment variables (.env file).
Keeps every secret / setting in one place.
"""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./atlas.db")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
DEFAULT_BRIEF_TIME = os.getenv("DEFAULT_BRIEF_TIME", "08:00")

# Fail fast with a clear message instead of a confusing crash later.
def validate_config():
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill these in."
        )
