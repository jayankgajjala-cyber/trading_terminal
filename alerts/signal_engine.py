"""
alerts/signal_engine.py — Runs every 5 minutes during market hours.
Evaluates best strategy signal for each symbol, fires alerts on transitions.
"""
import logging
from datetime import datetime, time as dtime
import pytz
import pandas as pd
from data.fetcher import get_historical_data
from analysis.technical import run_all_strategies, get_consensus
from data.cache import CacheManager
from alerts.emailer import send_alert_email
from config.settings import MARKET_OPEN_HOUR, MARKET_OPEN_MIN, MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN

logger = logging.getLogger(__name__)
cache = CacheManager()
IST = pytz.timezone("Asia/Kolkata")

# Track last signal per symbol to avoid duplicate alerts
_last_signals: dict[str, str] = {}


def is_market_hours() -> bool:
    now_ist = datetime.now(IST).time()
    market_open = dtime(MARKET_OPEN_HOUR, MARKET_OPEN_MIN)
    market_close = dtime(MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN)
    return market_open <= now_ist <= market_close


def check_signals(symbols: list[str], send_email: bool = True) -> list[dict]:
    """
    Check strategy signals for all symbols.
    Sends email for BUY/SELL transitions.
    Returns list of signal dicts.
    """
    signals = []
    for sym in symbols:
        try:
            df = get_historical_data(sym, period="2y")
            if df.empty:
                continue
            strategy_results = run_all_strategies(df)
            best_strategy = cache.get_best_strategy(sym) or "EMA Crossover"
            best_result = strategy_results.get(best_strategy, {})
            consensus = get_consensus(strategy_results)

            sig = {
                "symbol": sym,
                "signal": consensus["signal"],
                "confidence": consensus["confidence"],
                "best_strategy": best_strategy,
                "best_signal": best_result.get("signal", "HOLD"),
                "reason": best_result.get("reason", ""),
                "price": round(df["Close"].iloc[-1], 2),
                "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
            }
            signals.append(sig)
            cache.log_alert(sym, sig["signal"], sig["price"], best_strategy)

            # Alert on signal change (avoid spam)
            prev = _last_signals.get(sym, "HOLD")
            if sig["signal"] != "HOLD" and sig["signal"] != prev:
                _last_signals[sym] = sig["signal"]
                if send_email:
                    send_alert_email([sig])
        except Exception as e:
            logger.error(f"Signal check failed for {sym}: {e}")

    return signals


def scan_nifty500(symbols: list[str]) -> list[dict]:
    """Scan a broader list for opportunities (weekly)."""
    return check_signals(symbols, send_email=True)
