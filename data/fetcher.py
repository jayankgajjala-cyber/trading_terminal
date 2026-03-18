"""
data/fetcher.py — Historical OHLCV fetcher.
Priority: local cache → yfinance → Alpha Vantage (rate-limit safe).
Stores results in SQLite + Parquet for fast re-reads.
"""
import os
import time
import logging
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path
from data.cache import CacheManager
from config.settings import ALPHA_VANTAGE_KEY, CACHE_DIR

logger = logging.getLogger(__name__)
cache = CacheManager()

# Alpha Vantage free tier: 25 req/day
AV_BASE = "https://www.alphavantage.co/query"
AV_DAILY_LIMIT = 24  # leave one in reserve
_av_calls_today = 0

RETRY_BACKOFF = [1, 3, 7]  # seconds between retries


def _retry(func, *args, retries=3, **kwargs):
    for attempt, wait in enumerate(RETRY_BACKOFF[:retries]):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(wait)
    return None


def get_historical_data(symbol: str, period: str = "10y",
                        interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV data. Returns DataFrame with columns:
    Open, High, Low, Close, Volume. Index: DatetimeIndex.
    """
    cache_key = f"{symbol}_{period}_{interval}"
    cached = cache.load(cache_key)
    if cached is not None and not cached.empty:
        logger.info(f"Cache hit: {cache_key}")
        return cached

    logger.info(f"Fetching from yfinance: {symbol}")
    df = _retry(_yfinance_fetch, symbol, period, interval)
    if df is not None and not df.empty:
        cache.save(cache_key, df)
        return df

    logger.info(f"yfinance failed, trying Alpha Vantage: {symbol}")
    df = _alpha_vantage_fetch(symbol)
    if df is not None and not df.empty:
        cache.save(cache_key, df)
        return df

    logger.error(f"All sources failed for {symbol}")
    return pd.DataFrame()


def _yfinance_fetch(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Ensure symbol has .NS suffix for NSE stocks."""
    yf_sym = symbol if ("." in symbol) else f"{symbol}.NS"
    ticker = yf.Ticker(yf_sym)
    df = ticker.history(period=period, interval=interval, auto_adjust=True)
    if df.empty:
        raise ValueError(f"Empty data for {yf_sym}")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def _alpha_vantage_fetch(symbol: str) -> pd.DataFrame | None:
    """Alpha Vantage TIME_SERIES_DAILY_ADJUSTED — 20+ years history."""
    global _av_calls_today
    if _av_calls_today >= AV_DAILY_LIMIT:
        logger.warning("Alpha Vantage daily limit reached.")
        return None
    # Strip .NS suffix for AV — it uses BSE:RELIANCE or just RELIANCE
    av_sym = symbol.replace(".NS", "") + ".BSE"
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": av_sym,
        "outputsize": "full",
        "apikey": ALPHA_VANTAGE_KEY,
    }
    resp = requests.get(AV_BASE, params=params, timeout=20)
    _av_calls_today += 1
    data = resp.json()
    ts = data.get("Time Series (Daily)", {})
    if not ts:
        return None
    records = []
    for date_str, vals in ts.items():
        records.append({
            "Date": pd.Timestamp(date_str),
            "Open": float(vals["1. open"]),
            "High": float(vals["2. high"]),
            "Low": float(vals["3. low"]),
            "Close": float(vals["5. adjusted close"]),
            "Volume": int(vals["6. volume"]),
        })
    df = pd.DataFrame(records).set_index("Date").sort_index()
    return df


def get_bulk_data(symbols: list[str], period: str = "2y") -> dict[str, pd.DataFrame]:
    """Fetch multiple symbols. Respects rate limits with a 0.5s gap."""
    result = {}
    for sym in symbols:
        result[sym] = get_historical_data(sym, period=period)
        time.sleep(0.5)
    return result


def get_fundamental_data(symbol: str) -> dict:
    """Fetch fundamental metrics via yfinance info dict."""
    cache_key = f"fundamental_{symbol}"
    cached = cache.load_json(cache_key)
    if cached:
        return cached

    yf_sym = symbol if "." in symbol else f"{symbol}.NS"
    try:
        info = yf.Ticker(yf_sym).info
        fundamentals = {
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "debt_equity": info.get("debtToEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "eps": info.get("trailingEps"),
            "market_cap": info.get("marketCap"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "name": info.get("longName", symbol),
        }
        cache.save_json(cache_key, fundamentals, ttl_hours=24)
        return fundamentals
    except Exception as e:
        logger.error(f"Fundamental fetch failed for {symbol}: {e}")
        return {}
