"""
news/ai_analyst.py — AI News Intelligence Engine.

For each stock/article:
  1. Fetch from Google News RSS + NewsAPI
  2. Rule-based NLP: sentiment, event detection
  3. Impact scoring (short vs long term)
  4. AI-powered deep analysis via Claude API (optional, graceful fallback)
  5. Conflict detection: news vs technicals
  6. Confidence score
  7. Recommendation: BUY / HOLD / SELL with reasoning

Works 100% offline (rule-based). Claude API enhances quality when available.
"""
import re
import time
import json
import logging
import hashlib
import feedparser
import requests
from datetime import datetime
from data.cache import CacheManager

logger = logging.getLogger(__name__)
cache  = CacheManager()

# ── Sentiment lexicons ────────────────────────────────────────────────────────
BULL_STRONG = [
    "record profit","record revenue","beats estimates","blowout earnings",
    "strong results","profit surge","revenue surge","raises guidance",
    "upgraded","buy rating","strong buy","outperform","all-time high",
    "52-week high","breakout","acquisition boost","market share gain",
    "mega order","buyback","dividend hike","debt free","new product launch",
    "fda approval","regulatory approval","contract win","capex expansion",
    "highest ever","landmark deal","best quarter",
]
BULL_MILD = [
    "profit","growth","revenue up","sales up","positive","optimistic","strong",
    "recovery","rebound","improve","beat","higher","gain","increase","rise",
    "boost","upgrade","partnership","deal","order","margin improvement",
    "cost reduction","efficiency","expansion","launch","hiring",
]
BEAR_STRONG = [
    "fraud","scam","investigation","sebi notice","rbi penalty","default",
    "bankruptcy","insolvency","massive loss","profit crash","revenue decline",
    "guidance cut","downgraded","sell rating","underperform","all-time low",
    "52-week low","breakdown","supply chain crisis","recall","legal action",
    "ceo arrested","promoter pledge","fii selling","block deal at discount",
    "rights issue at discount","npa spike","bad loans","write-off",
]
BEAR_MILD = [
    "loss","decline","fall","drop","miss","disappointing","weak","concerns",
    "pressure","risk","challenges","headwinds","slowdown","delay","cut",
    "reduce","lower guidance","tariff","inflation impact","margin squeeze",
]
EVENT_PATTERNS = {
    "earnings":       ["quarterly results","q[1-4] results","earnings","profit","revenue","eps","pat"],
    "merger_acq":     ["acqui","merge","takeover","buyout","stake","m&a"],
    "regulatory":     ["sebi","rbi","government","policy","regulation","compliance","penalty","notice"],
    "management":     ["ceo","md","cfo","board","director","appoint","resign","leadership"],
    "macro":          ["rbi rate","inflation","gdp","fed","global","oil price","rupee","dollar"],
    "capex":          ["capex","expansion","plant","capacity","investment","greenfield"],
    "product":        ["launch","product","patent","fda","approval","new service"],
    "block_deal":     ["block deal","bulk deal","fii","dii","promoter"],
}


# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean_text(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _score_text(text: str) -> dict:
    """Score text for bullish/bearish signals. Returns raw counts."""
    t   = _clean_text(text)
    bs  = sum(1 for w in BULL_STRONG if w in t)
    bm  = sum(1 for w in BULL_MILD   if w in t)
    brs = sum(1 for w in BEAR_STRONG if w in t)
    brm = sum(1 for w in BEAR_MILD   if w in t)
    return {"bull_strong": bs, "bull_mild": bm, "bear_strong": brs, "bear_mild": brm}


def _detect_events(text: str) -> list:
    t = _clean_text(text)
    found = []
    for event_type, keywords in EVENT_PATTERNS.items():
        if any(re.search(kw, t) for kw in keywords):
            found.append(event_type)
    return found


def _compute_sentiment(sc: dict, events: list) -> dict:
    """
    Convert raw scores to sentiment + score (-1 to +1).
    """
    bull = sc["bull_strong"] * 3 + sc["bull_mild"]
    bear = sc["bear_strong"] * 3 + sc["bear_mild"]
    net  = bull - bear
    total = bull + bear

    # Normalise
    if total == 0:
        norm = 0.0
    else:
        norm = max(-1.0, min(1.0, net / max(total, 1)))

    if norm > 0.25:    label = "BULLISH"
    elif norm < -0.25: label = "BEARISH"
    else:              label = "NEUTRAL"

    # Boost confidence if strong keywords found
    base_conf = 40
    base_conf += sc["bull_strong"] * 10 + sc["bear_strong"] * 10
    base_conf += len(events) * 5
    conf = min(base_conf, 85)

    return {"label": label, "score": round(norm, 3), "confidence": conf}


def _impact_assessment(events: list, sentiment: dict) -> dict:
    """
    Classify short-term vs long-term impact.
    """
    short_impact = "NEUTRAL"
    long_impact  = "NEUTRAL"
    label = sentiment["label"]

    short_triggers = {"earnings", "block_deal", "regulatory"}
    long_triggers  = {"merger_acq", "capex", "product", "management", "macro"}

    if any(e in short_triggers for e in events):
        short_impact = label
    if any(e in long_triggers for e in events):
        long_impact = label

    # If no specific trigger, default to short-term
    if short_impact == "NEUTRAL" and long_impact == "NEUTRAL" and label != "NEUTRAL":
        short_impact = label

    return {"short_term": short_impact, "long_term": long_impact}


def _rule_based_summary(articles: list, symbol: str) -> dict:
    """
    Synthesise multiple articles into a stock-level insight using rule-based NLP.
    Returns the full insight dict.
    """
    if not articles:
        return {
            "symbol":      symbol,
            "summary":     "No recent news found.",
            "takeaway":    "Insufficient news data.",
            "risk":        "Unknown",
            "sentiment":   "NEUTRAL",
            "sent_score":  0.0,
            "events":      [],
            "short_impact":"NEUTRAL",
            "long_impact": "NEUTRAL",
            "recommendation": "HOLD",
            "news_reason": "No news to analyse",
            "confidence":  30,
            "articles_used": 0,
        }

    # Combine text from top 5 articles
    combined = " ".join([
        f"{a.get('title','')} {a.get('description','')}"
        for a in articles[:5]
    ])
    sc      = _score_text(combined)
    events  = _detect_events(combined)
    senti   = _compute_sentiment(sc, events)
    impact  = _impact_assessment(events, senti)

    # Consistent sentiment across articles
    individual_sentiments = []
    for a in articles[:5]:
        text = f"{a.get('title','')} {a.get('description','')}"
        s    = _score_text(text)
        si   = _compute_sentiment(s, _detect_events(text))
        individual_sentiments.append(si["label"])

    n_bull  = individual_sentiments.count("BULLISH")
    n_bear  = individual_sentiments.count("BEARISH")
    n_neut  = individual_sentiments.count("NEUTRAL")
    consistency = max(n_bull, n_bear, n_neut) / max(len(individual_sentiments), 1) * 100

    # Boost confidence for consistency
    conf = senti["confidence"]
    conf = min(conf + int(consistency / 10), 90)

    # Build human-readable summary
    sym_clean = symbol.replace(".NS", "")
    event_labels = {
        "earnings": "quarterly earnings", "merger_acq": "M&A activity",
        "regulatory": "regulatory developments", "management": "management changes",
        "macro": "macro/policy factors", "capex": "capex/expansion plans",
        "product": "product/approval news", "block_deal": "institutional activity",
    }
    detected_str = ", ".join(event_labels.get(e, e) for e in events[:3]) if events else "general market news"

    if senti["label"] == "BULLISH":
        summary = (f"{sym_clean} shows positive momentum driven by {detected_str}. "
                   f"{n_bull} of {len(articles[:5])} recent articles carry a bullish tone.")
        takeaway = f"Positive near-term catalyst. Monitor for follow-through."
        risk     = "Valuation risk if rally outpaces fundamentals."
        rec      = "BUY" if senti["score"] > 0.4 else "HOLD"
        news_reason = f"Bullish news ({senti['score']:+.2f}) on {detected_str}"
    elif senti["label"] == "BEARISH":
        summary = (f"{sym_clean} faces headwinds: {detected_str} has been flagged negatively. "
                   f"{n_bear} of {len(articles[:5])} articles carry a bearish tone.")
        takeaway = f"Negative near-term pressure. Risk of further downside."
        risk     = "Further downside if bearish factors persist."
        rec      = "SELL" if senti["score"] < -0.4 else "HOLD"
        news_reason = f"Bearish news ({senti['score']:+.2f}) on {detected_str}"
    else:
        summary = (f"{sym_clean} has mixed/neutral news. Events covered: {detected_str}. "
                   f"No clear directional bias from recent coverage.")
        takeaway = "No strong news catalyst. Technicals should drive the decision."
        risk     = "Low visibility — news flow may shift quickly."
        rec      = "HOLD"
        news_reason = f"Neutral news ({senti['score']:+.2f})"

    return {
        "symbol":        symbol,
        "summary":       summary,
        "takeaway":      takeaway,
        "risk":          risk,
        "sentiment":     senti["label"],
        "sent_score":    senti["score"],
        "events":        events,
        "short_impact":  impact["short_term"],
        "long_impact":   impact["long_term"],
        "recommendation": rec,
        "news_reason":   news_reason,
        "confidence":    conf,
        "articles_used": len(articles[:5]),
        "consistency_pct": round(consistency, 0),
    }


def _claude_enhance(articles: list, symbol: str, rule_result: dict) -> dict:
    """
    Optional: use Claude API to generate a higher-quality summary.
    Falls back to rule_result if API is unavailable.
    """
    try:
        import streamlit as st
        api_key = st.secrets.get("anthropic", {}).get("API_KEY", "")
    except Exception:
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not api_key:
        return rule_result   # graceful fallback

    headlines = "\n".join([
        f"- {a.get('title','')}: {(a.get('description','') or '')[:120]}"
        for a in articles[:5]
    ])
    sym_clean = symbol.replace(".NS", "")

    prompt = f"""You are a professional equity analyst for Indian stock markets.
Analyse the following recent news headlines for {sym_clean} (NSE-listed stock).

HEADLINES:
{headlines}

Return ONLY a valid JSON object with these exact keys:
{{
  "summary": "2-3 sentence factual summary of the news",
  "takeaway": "single key insight for an investor",
  "risk": "main risk factor if any, or 'None identified'",
  "sentiment": "BULLISH or BEARISH or NEUTRAL",
  "short_term_impact": "POSITIVE or NEGATIVE or NEUTRAL",
  "long_term_impact": "POSITIVE or NEGATIVE or NEUTRAL",
  "recommendation": "BUY or HOLD or SELL",
  "reasoning": "one sentence justification"
}}
Respond ONLY with the JSON. No preamble, no markdown."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 400,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        if resp.status_code == 200:
            raw  = resp.json()["content"][0]["text"].strip()
            data = json.loads(raw)
            # Merge AI result into rule_result
            rule_result.update({
                "summary":       data.get("summary",       rule_result["summary"]),
                "takeaway":      data.get("takeaway",      rule_result["takeaway"]),
                "risk":          data.get("risk",          rule_result["risk"]),
                "sentiment":     data.get("sentiment",     rule_result["sentiment"]),
                "short_impact":  data.get("short_term_impact", rule_result["short_impact"]),
                "long_impact":   data.get("long_term_impact",  rule_result["long_impact"]),
                "recommendation":data.get("recommendation",rule_result["recommendation"]),
                "news_reason":   data.get("reasoning",     rule_result["news_reason"]),
                "ai_enhanced":   True,
                "confidence":    min(rule_result["confidence"] + 10, 95),
            })
    except Exception as e:
        logger.debug(f"Claude enhance failed (fallback to rule-based): {e}")

    return rule_result


def detect_conflict(news_insight: dict, tech_signal: dict) -> dict:
    """
    Compare news sentiment vs technical signal.
    Returns conflict dict with explanation.
    """
    ns = news_insight.get("sentiment", "NEUTRAL")
    ts = tech_signal.get("signal", "HOLD")
    nc = news_insight.get("confidence", 50)
    tc = tech_signal.get("confidence", 0) * 100

    # Map to comparable directions
    news_dir = "BULLISH" if ns == "BULLISH" else "BEARISH" if ns == "BEARISH" else "NEUTRAL"
    tech_dir = "BULLISH" if ts == "BUY" else "BEARISH" if ts == "SELL" else "NEUTRAL"

    conflict = (news_dir != tech_dir and
                news_dir != "NEUTRAL" and tech_dir != "NEUTRAL")

    if conflict:
        explanation = (
            f"News sentiment is {news_dir} (confidence {nc}%) "
            f"but technical signal is {tech_dir} ({ts}, confidence {tc:.0f}%). "
            f"This conflict suggests caution — wait for both signals to align before acting."
        )
        action = "WAIT — conflicting signals. Higher risk trade."
    elif news_dir == tech_dir and news_dir != "NEUTRAL":
        explanation = (
            f"News and technicals both {news_dir} — confluent signal. "
            f"Higher conviction trade."
        )
        action = f"CONFIRMED {ts} — news + technicals agree"
    else:
        explanation = "One or both signals are neutral. Insufficient conviction."
        action = "HOLD — mixed or neutral signals"

    return {
        "has_conflict": conflict,
        "news_direction": news_dir,
        "tech_direction": tech_dir,
        "explanation":    explanation,
        "action":         action,
    }


def get_stock_news_insight(symbol: str, articles: list = None,
                           tech_signal: dict = None,
                           use_claude: bool = True) -> dict:
    """
    Main entry point. Returns complete news insight for one stock.
    Caches results for 2 hours to avoid redundant fetches.
    """
    cache_key = f"news_insight_{symbol}"
    cached = cache.load_json(cache_key)
    if cached:
        return cached

    # Fetch news if not provided
    if not articles:
        try:
            from news.fetcher import fetch_stock_news
            articles = fetch_stock_news(symbol)
        except Exception as e:
            logger.warning(f"News fetch failed for {symbol}: {e}")
            articles = []

    # Rule-based analysis
    insight = _rule_based_summary(articles, symbol)

    # Claude enhancement (optional)
    if use_claude and articles:
        insight = _claude_enhance(articles, symbol, insight)

    # Conflict detection
    if tech_signal:
        conflict = detect_conflict(insight, tech_signal)
        insight["conflict"] = conflict
    else:
        insight["conflict"] = {"has_conflict": False, "explanation": "", "action": ""}

    # Combined recommendation
    if tech_signal and not insight["conflict"]["has_conflict"]:
        # Both agree — use higher-confidence direction
        ts   = tech_signal.get("signal", "HOLD")
        t_c  = tech_signal.get("confidence", 0) * 100
        n_r  = insight["recommendation"]
        n_c  = insight["confidence"]
        if ts != "HOLD" and n_r != "HOLD" and ts == n_r:
            combined_conf = round((t_c * 0.6 + n_c * 0.4), 0)
            insight["combined_recommendation"] = ts
            insight["combined_confidence"]     = combined_conf
            insight["combined_reason"]         = (
                f"{ts} — {insight['news_reason']} + "
                f"Tech: {tech_signal.get('reason','')[:60]}"
            )
        else:
            insight["combined_recommendation"] = "HOLD"
            insight["combined_confidence"]     = 50
            insight["combined_reason"]         = "Signals do not fully agree — holding"
    else:
        insight["combined_recommendation"] = insight["recommendation"]
        insight["combined_confidence"]     = insight["confidence"]
        insight["combined_reason"]         = insight["news_reason"]

    cache.save_json(cache_key, insight, ttl_hours=2)
    return insight


def get_portfolio_insights(symbols: list, tech_signals: dict = None,
                            use_claude: bool = True) -> dict:
    """
    Run news intelligence for all portfolio stocks.
    tech_signals: dict keyed by symbol → signal dict (optional).
    Returns dict keyed by symbol.
    """
    results = {}
    for sym in symbols:
        tech = (tech_signals or {}).get(sym)
        try:
            results[sym] = get_stock_news_insight(sym, tech_signal=tech, use_claude=use_claude)
        except Exception as e:
            logger.error(f"Insight failed for {sym}: {e}")
            results[sym] = {
                "symbol": sym, "summary": f"Analysis failed: {e}",
                "sentiment": "NEUTRAL", "recommendation": "HOLD",
                "confidence": 0, "conflict": {}
            }
        time.sleep(0.3)   # gentle rate limit
    return results
