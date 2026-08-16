"""
Wrapper around Alpha Vantage's free API for live financial data.
This is the "tool" the LLM calls when it needs real, current numbers
instead of guessing from its training data.

Free tier limits: ~25 requests/day, 5/minute (as of writing) - fine for
an MVP/demo. If you hit limits, Finnhub is a good free alternative.
"""
import httpx
from app.config import ALPHA_VANTAGE_API_KEY

BASE_URL = "https://www.alphavantage.co/query"


async def get_quote(symbol: str) -> dict:
    """Get the latest price quote for a stock symbol (e.g. 'AAPL')."""
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        data = resp.json()

    quote = data.get("Global Quote", {})
    if not quote:
        return {"error": f"No data found for symbol '{symbol}'. It may be invalid or the API limit was hit."}

    return {
        "symbol": quote.get("01. symbol"),
        "price": quote.get("05. price"),
        "change": quote.get("09. change"),
        "change_percent": quote.get("10. change percent"),
        "volume": quote.get("06. volume"),
        "latest_trading_day": quote.get("07. latest trading day"),
    }


async def get_company_overview(symbol: str) -> dict:
    """Get company fundamentals: sector, market cap, PE ratio, description, etc."""
    params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        data = resp.json()

    if not data or "Symbol" not in data:
        return {"error": f"No company overview found for '{symbol}'."}

    return {
        "name": data.get("Name"),
        "sector": data.get("Sector"),
        "industry": data.get("Industry"),
        "description": data.get("Description"),
        "market_cap": data.get("MarketCapitalization"),
        "pe_ratio": data.get("PERatio"),
        "eps": data.get("EPS"),
        "52_week_high": data.get("52WeekHigh"),
        "52_week_low": data.get("52WeekLow"),
        "analyst_target_price": data.get("AnalystTargetPrice"),
    }


async def get_company_news(symbol: str, limit: int = 5) -> dict:
    """Get recent news sentiment for a company."""
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(BASE_URL, params=params)
        data = resp.json()

    feed = data.get("feed", [])
    if not feed:
        return {"error": f"No recent news found for '{symbol}'."}

    articles = [
        {
            "title": item.get("title"),
            "summary": item.get("summary"),
            "source": item.get("source"),
            "sentiment": item.get("overall_sentiment_label"),
            "time_published": item.get("time_published"),
            "url": item.get("url"),
        }
        for item in feed[:limit]
    ]
    return {"articles": articles}


# Tool definitions in the format the LLM needs to know what it can call.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Get the current stock price and daily change for a company by its ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL, MSFT, TSLA"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_overview",
            "description": "Get company fundamentals: sector, market cap, PE ratio, description, 52-week range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL, MSFT, TSLA"}
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_news",
            "description": "Get recent news articles and sentiment for a company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. AAPL, MSFT, TSLA"}
                },
                "required": ["symbol"],
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "get_quote": get_quote,
    "get_company_overview": get_company_overview,
    "get_company_news": get_company_news,
}
