# Atlas — AI Financial Assistant (Telegram)

A conversational AI financial assistant that lives inside Telegram. Built for
the Atlas AI Financial Assistant Hackathon.

## What it does (MVP scope)

1. **Conversational onboarding** — learns your role, watchlist, and preferred
   brief time through natural back-and-forth, not a form. Skippable at every step.
2. **Daily intelligence** — checks your watchlist every morning at your chosen
   time and sends a brief only if something moved significantly. Silent otherwise.
3. **Natural Q&A + research** — ask about any company, compare stocks, get
   real-time quotes and news, all via natural conversation (no commands).

## Stack (100% free tier)

- **Backend:** Python + FastAPI-adjacent structure (bot runs via polling, no server needed)
- **Bot:** python-telegram-bot (polling mode — no public URL required)
- **AI:** Groq (llama-3.3-70b-versatile) — free tier, tool-calling enabled
- **Database:** SQLite (zero setup)
- **Financial data:** Alpha Vantage free tier
- **Scheduler:** APScheduler (in-process cron for daily briefs)

## Setup

1. **Get your Telegram bot token**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot`, follow the prompts, copy the token it gives you

2. **Get a free Groq API key**
   - Sign up at https://console.groq.com (no credit card required)
   - Create an API key

3. **Get a free Alpha Vantage API key**
   - Sign up at https://www.alphavantage.co/support/#api-key (instant, free)

4. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Then open `.env` and fill in your three keys/tokens.

6. **Run the bot**
   ```bash
   python run.py
   ```

7. Open Telegram, find your bot by the username you gave it, and send `/start`.

## Project structure

```
atlas-finance-bot/
├── app/
│   ├── bot.py              # Telegram handlers (entry point for messages)
│   ├── config.py            # env var loading
│   ├── database.py          # SQLAlchemy models (User, WatchlistItem, Message)
│   ├── llm.py                # Groq client + tool-calling loop
│   ├── scheduler.py          # daily brief background job
│   ├── handlers/
│   │   ├── onboarding.py     # conversational onboarding state machine
│   │   └── conversation.py   # normal chat turns, memory loading
│   └── tools/
│       └── financial_data.py # Alpha Vantage wrapper + tool definitions for the LLM
├── requirements.txt
├── .env.example
└── run.py
```

## What's stubbed out (next steps)

- **Voice messages** — hook exists in `handle_voice()` in `app/bot.py`.
  Wire up transcription (Groq has a free Whisper-compatible endpoint).
- **Image understanding** — hook exists in `handle_photo()` in `app/bot.py`.
  Wire up a vision-capable model call for charts/screenshots.
- **Document upload (PDF Q&A)** — not yet implemented. Add a handler for
  `filters.Document`, extract text (e.g. with `pypdf`), and feed it into
  the conversation as context.
- **Gmail / Calendar integration** — optional per the assignment; add only
  after the core 3 pillars are solid.

## Design notes

- No slash commands, buttons, or menus are used for the core experience
  (per the assignment's requirements) — `/start` is the one necessary
  exception, since it's Telegram's own convention for initiating a bot chat.
- The daily brief deliberately stays silent if nothing moved significantly
  (≥1% change) — quality over frequency, per the design principles.
- Onboarding state is currently in-memory (`_onboarding_state` dict in
  `onboarding.py`). Fine for a single-process demo; move to a DB column
  if you need to survive restarts or scale to multiple workers.
