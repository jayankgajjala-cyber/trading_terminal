"""
news/fetcher.py — Aggregates news from NewsAPI + Google News RSS.
Returns sorted list of articles (latest first).
"""
import logging
import time
import feedparser
import requests
from data.cache import CacheManager
from config.settings import NEWS_API_KEY

logger = logging.getLogger(__name__)
cache = CacheManager()


def _google_news_rss(query: str) -> list[dict]:
    """Scrape Google News RSS — no API key needed."""
    url = f"https://news.google.com/rss/search?q={query}+stock+India&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:8]:
            articles.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
                "publishedAt": entry.get("published", ""),
                "description": entry.get("summary", "")[:200],
            })
        return articles
    except Exception as e:
        logger.warning(f"Google News RSS failed for '{query}': {e}")
        return []


def _newsapi_fetch(query: str, page_size: int = 10) -> list[dict]:
    """NewsAPI free tier: 100 req/day, 1 month history."""
    if not NEWS_API_KEY:
        return []
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": f"{query} NSE India stock",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "language": "en",
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        return data.get("articles", [])
    except Exception as e:
        logger.warning(f"NewsAPI failed for '{query}': {e}")
        return []


def fetch_all_news(symbols: list[str], include_global: bool = True) -> list[dict]:
    """
    Fetch news for portfolio symbols + Nifty/India macro.
    Returns deduplicated, latest-first list.
    """
    cache_key = f"news_{'_'.join(symbols[:5])}"
    cached = cache.load_json(cache_key)
    if cached:
        return cached.get("articles", [])

    all_articles = []
    seen_titles = set()

    # Global macro + India market
    if include_global:
        for query in ["Nifty 50", "RBI interest rate", "India market", "Sensex"]:
            all_articles += _google_news_rss(query)
            time.sleep(0.3)

    # Per-symbol news
    for sym in symbols[:15]:
        clean = sym.replace(".NS", "").replace(".BSE", "")
        articles = _newsapi_fetch(clean, page_size=5)
        if not articles:
            articles = _google_news_rss(clean)
        all_articles += articles
        time.sleep(0.2)

    # Deduplicate and sort
    result = []
    for a in all_articles:
        title = a.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            result.append(a)

    result.sort(key=lambda x: x.get("publishedAt", ""), reverse=True)
    cache.save_json(cache_key, {"articles": result}, ttl_hours=1)
    return result


def fetch_nifty_changes() -> list[dict]:
    """Stub: monitor Nifty 50 reconstitution announcements."""
    query = "Nifty 50 index inclusion exclusion 2025"
    return _google_news_rss(query)
