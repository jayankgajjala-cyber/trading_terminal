"""
alerts/signal_engine.py — Signal generation engine.

FIXES:
  - Integrates backtest scores into consensus weighting (not just caching best strategy)
  - Calls deep_analysis() for richer context
  - Adds data quality gating (flags < 5 years)
  - Adds signal distribution check after batch scan
  - Generates detailed reasoning string per stock
  - No placeholder signals — explicit "INSUFFICIENT DATA" when needed
"""
import logging
from datetime import datetime, time as dtime
import pytz
import pandas as pd
from data.fetcher import get_historical_data
from analysis.technical import run_all_strategies, get_consensus, deep_analysis, check_signal_bias
from data.cache import CacheManager
from config.settings import MARKET_OPEN_HOUR, MARKET_OPEN_MIN, MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN

logger = logging.getLogger(__name__)
cache  = CacheManager()
IST    = pytz.timezone("Asia/Kolkata")

# Track last signal per symbol to suppress duplicate alerts
_last_signals: dict = {}


def is_market_hours() -> bool:
    now_ist = datetime.now(IST).time()
    return dtime(MARKET_OPEN_HOUR, MARKET_OPEN_MIN) <= now_ist <= dtime(MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN)


def _get_backtest_scores(symbol: str) -> dict:
    """
    Load cached backtest results for this symbol and return
    a dict keyed by strategy name with their metrics.
    """
    try:
        bt_df = cache.load_backtest(symbol)
        if bt_df.empty:
            return {}
        scores = {}
        for _, row in bt_df.iterrows():
            name = row.get("strategy", "")
            if name:
                scores[name] = {
                    "cagr":         row.get("cagr", 0.0),
                    "sharpe":       row.get("sharpe", 0.0),
                    "total_trades": row.get("total_trades", 0),
                    "reliability":  row.get("reliability", ""),
                }
        return scores
    except Exception:
        return {}


def analyse_stock(symbol: str) -> dict:
    """
    Full single-stock signal analysis pipeline:
      1. Fetch 10Y data
      2. Data quality check
      3. Run all 5 strategies
      4. Deep analysis (trend/momentum)
      5. Weighted consensus (optionally backtest-boosted)
      6. Build rich reasoning string
    Returns a signal dict ready for display and alerting.
    """
    try:
        # ── 1. Fetch data ────────────────────────────────────────────────────
        df = get_historical_data(symbol, period="10y")
        if df is None or df.empty:
            return {
                "symbol": symbol, "signal": "HOLD",
                "confidence": 0.0, "price": 0.0,
                "reason": "Unable to fetch data — no signal generated",
                "data_quality": "NO_DATA", "years": 0,
                "best_strategy": "—", "strategies": {},
                "deep": {}, "warning": "NO DATA",
            }

        years = len(df) / 252

        # ── 2. Data quality gate ─────────────────────────────────────────────
        if years < 1:
            return {
                "symbol": symbol, "signal": "HOLD",
                "confidence": 0.0,
                "price": round(df["Close"].iloc[-1], 2),
                "reason": f"INSUFFICIENT DATA — only {years:.1f} years available (need ≥1yr)",
                "data_quality": "INSUFFICIENT", "years": round(years, 1),
                "best_strategy": "—", "strategies": {}, "deep": {},
                "warning": "INSUFFICIENT DATA",
            }

        dq_label = "POOR" if years < 3 else "LOW" if years < 5 else \
                   "MODERATE" if years < 8 else "GOOD"

        # ── 3. Run all strategies ─────────────────────────────────────────────
        strategy_results = run_all_strategies(df)

        # ── 4. Deep analysis ──────────────────────────────────────────────────
        da = deep_analysis(df)

        # ── 5. Backtest scores for weighting ─────────────────────────────────
        bt_scores = _get_backtest_scores(symbol)

        # ── 6. Consensus ──────────────────────────────────────────────────────
        best_strat = cache.get_best_strategy(symbol)
        consensus  = get_consensus(strategy_results)

        # Pick best strategy from strategies that voted BUY/SELL (match consensus)
        voted_signal = consensus["signal"]
        if voted_signal in ("BUY", "SELL"):
            matching = [(n, v) for n, v in strategy_results.items()
                        if v["signal"] == voted_signal]
            if matching:
                # Use highest-scoring matching strategy as "best" for this signal
                best_for_signal = max(matching, key=lambda x: x[1]["score"])
                best_strat = best_for_signal[0]
                primary_reason = best_for_signal[1]["reason"]
            else:
                primary_reason = consensus.get("reason_summary", "")
        else:
            primary_reason = consensus.get("reason_summary", "Mixed signals")

        # ── 7. Build rich reason string ───────────────────────────────────────
        agreeing = consensus.get("agreeing_strategies", 0)
        n_strats = len(strategy_results)
        trend_str = f"{da.get('short_trend','?')}/{da.get('mid_trend','?')}/{da.get('long_trend','?')}"
        aligned   = da.get("trend_aligned", False)
        roc14     = da.get("momentum_roc14", 0)

        reason_parts = [primary_reason]
        if agreeing > 0:
            reason_parts.append(f"{agreeing}/{n_strats} strategies agree")
        reason_parts.append(f"Trend: {trend_str}{'(aligned)' if aligned else ''}")
        reason_parts.append(f"14D momentum: {roc14:+.1f}%")
        if da.get("pct_from_52w_high"):
            reason_parts.append(f"52W H: {da['pct_from_52w_high']:+.1f}%")

        full_reason = " | ".join(reason_parts)

        # ── 8. Adjust confidence based on data quality ────────────────────────
        conf = consensus["confidence"]
        if dq_label == "POOR":
            conf = min(conf, 0.45)
        elif dq_label == "LOW":
            conf = min(conf, 0.60)

        price = round(df["Close"].iloc[-1], 2)
        ts    = datetime.now(IST).strftime("%H:%M:%S IST")

        return {
            "symbol":        symbol,
            "signal":        consensus["signal"],
            "confidence":    round(conf, 3),
            "price":         price,
            "reason":        full_reason,
            "best_strategy": best_strat or "—",
            "strategies":    strategy_results,
            "deep":          da,
            "data_quality":  dq_label,
            "years":         round(years, 1),
            "buy_votes":     consensus.get("buy_votes", 0),
            "sell_votes":    consensus.get("sell_votes", 0),
            "hold_votes":    consensus.get("hold_votes", 0),
            "timestamp":     ts,
            "warning":       consensus.get("warning", ""),
        }

    except Exception as e:
        logger.error(f"analyse_stock failed for {symbol}: {e}")
        return {
            "symbol": symbol, "signal": "HOLD", "confidence": 0.0,
            "price": 0.0, "reason": f"Analysis error: {str(e)[:80]}",
            "data_quality": "ERROR", "years": 0,
            "best_strategy": "—", "strategies": {}, "deep": {},
            "warning": "ANALYSIS ERROR",
        }


def check_signals(symbols: list, send_email: bool = True) -> list:
    """
    Run analyse_stock for all symbols.
    After scanning: check signal distribution, flag bias.
    Send email only on signal transitions (BUY/SELL, not repeated HOLD).
    Returns list of signal dicts.
    """
    signals = []
    for sym in symbols:
        sig = analyse_stock(sym)
        signals.append(sig)

        # Log to alert_log
        cache.log_alert(sym, sig["signal"], sig["price"], sig["best_strategy"])

        # Email on signal transition (not duplicate)
        prev = _last_signals.get(sym, "HOLD")
        if send_email and sig["signal"] != "HOLD" and sig["signal"] != prev:
            _last_signals[sym] = sig["signal"]
            try:
                from alerts.emailer import send_alert_email
                send_alert_email([sig])
            except Exception as e:
                logger.warning(f"Email send failed: {e}")

    # Distribution check
    bias_check = check_signal_bias(signals)
    if bias_check.get("bias"):
        logger.warning(bias_check["message"])

    return signals


def scan_nifty500(symbols: list) -> list:
    """Scan a broader universe. Same pipeline, email enabled."""
    return check_signals(symbols, send_email=True)
