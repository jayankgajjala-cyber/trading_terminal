"""
analysis/technical.py — All technical strategies + deep analysis.
Fixed: consensus threshold, signal bias detection, deep research mode.
"""
import pandas as pd
import numpy as np
import ta
from config.settings import (EMA_SHORT, EMA_LONG, RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
                    MACD_FAST, MACD_SLOW, MACD_SIGNAL, BB_PERIOD, BB_STD,
                    VOLUME_SPIKE_MULTIPLIER)


def _base_signal() -> dict:
    return {"signal": "HOLD", "reason": "Insufficient data", "score": 0.0}


def ema_crossover(df: pd.DataFrame) -> dict:
    """Golden Cross / Death Cross on 50/200 EMA. Also signals trend continuation."""
    if len(df) < EMA_LONG + 5:
        return _base_signal()
    df = df.copy()
    df["ema_short"] = df["Close"].ewm(span=EMA_SHORT, adjust=False).mean()
    df["ema_long"]  = df["Close"].ewm(span=EMA_LONG,  adjust=False).mean()
    last = df.iloc[-1]
    prev = df.iloc[-2]

    cross_up   = prev["ema_short"] <= prev["ema_long"] and last["ema_short"] > last["ema_long"]
    cross_down = prev["ema_short"] >= prev["ema_long"] and last["ema_short"] < last["ema_long"]
    above      = last["ema_short"] > last["ema_long"]
    gap_pct    = abs(last["ema_short"] - last["ema_long"]) / last["ema_long"] * 100

    # How fast is price moving vs the long EMA? (momentum proxy)
    ema_slope = (df["ema_long"].iloc[-1] - df["ema_long"].iloc[-10]) / df["ema_long"].iloc[-10] * 100

    if cross_up:
        return {"signal": "BUY",  "reason": f"Golden Cross: 50 EMA crossed above 200 EMA (gap {gap_pct:.1f}%)", "score": 0.92}
    if cross_down:
        return {"signal": "SELL", "reason": f"Death Cross: 50 EMA crossed below 200 EMA (gap {gap_pct:.1f}%)", "score": 0.92}

    # Continuation signals — not just HOLD when trend is strong
    if above and gap_pct > 3 and ema_slope > 0.2:
        return {"signal": "BUY",  "reason": f"Strong uptrend: 50 EMA {gap_pct:.1f}% above 200 EMA, rising slope", "score": 0.68}
    if not above and gap_pct > 3 and ema_slope < -0.2:
        return {"signal": "SELL", "reason": f"Strong downtrend: 50 EMA {gap_pct:.1f}% below 200 EMA, falling slope", "score": 0.65}
    if above:
        return {"signal": "HOLD", "reason": f"Bullish structure (gap {gap_pct:.1f}%) but momentum weak", "score": 0.55}
    return {"signal": "HOLD", "reason": f"Bearish structure (gap {gap_pct:.1f}%) but no acceleration", "score": 0.45}


def rsi_macd(df: pd.DataFrame) -> dict:
    """RSI oversold/overbought + MACD histogram cross + divergence check."""
    if len(df) < MACD_SLOW + MACD_SIGNAL + 5:
        return _base_signal()
    df = df.copy()
    df["rsi"]       = ta.momentum.RSIIndicator(df["Close"], window=RSI_PERIOD).rsi()
    macd_ind        = ta.trend.MACD(df["Close"], window_fast=MACD_FAST,
                                     window_slow=MACD_SLOW, window_sign=MACD_SIGNAL)
    df["macd_hist"] = macd_ind.macd_diff()
    df["macd_line"] = macd_ind.macd()
    df["sig_line"]  = macd_ind.macd_signal()

    r           = df.iloc[-1]["rsi"]
    hist        = df.iloc[-1]["macd_hist"]
    prev_hist   = df.iloc[-2]["macd_hist"]
    macd_val    = df.iloc[-1]["macd_line"]

    cross_up    = prev_hist < 0 and hist > 0
    cross_down  = prev_hist > 0 and hist < 0
    hist_growing = hist > prev_hist

    reasons = []
    score   = 0.5
    signal  = "HOLD"

    # RSI signals
    if r < RSI_OVERSOLD:
        reasons.append(f"RSI oversold ({r:.1f})")
        score += 0.22
        signal = "BUY"
    elif r < 40:
        reasons.append(f"RSI weak ({r:.1f}), approaching oversold")
        score += 0.10
        signal = "BUY"
    elif r > RSI_OVERBOUGHT:
        reasons.append(f"RSI overbought ({r:.1f})")
        score += 0.22
        signal = "SELL"
    elif r > 60:
        reasons.append(f"RSI strong ({r:.1f})")
        score += 0.10
        signal = "BUY"

    # MACD signals
    if cross_up:
        reasons.append("MACD bullish histogram cross")
        score  = min(score + 0.28, 1.0)
        signal = "BUY"
    elif cross_down:
        reasons.append("MACD bearish histogram cross")
        score  = min(score + 0.28, 1.0)
        signal = "SELL"
    elif hist > 0 and hist_growing:
        reasons.append(f"MACD histogram positive and expanding ({hist:.2f})")
        score += 0.12
        signal = "BUY" if signal == "HOLD" else signal
    elif hist < 0 and not hist_growing:
        reasons.append(f"MACD histogram negative and falling ({hist:.2f})")
        score += 0.12
        signal = "SELL" if signal == "HOLD" else signal

    reason_text = " | ".join(reasons) if reasons else f"RSI neutral ({r:.1f}), MACD flat"
    return {"signal": signal, "reason": reason_text, "score": min(score, 0.95)}


def bollinger_bands(df: pd.DataFrame) -> dict:
    """BB squeeze, band touch, and mean-reversion signals."""
    if len(df) < BB_PERIOD + 5:
        return _base_signal()
    df = df.copy()
    bb         = ta.volatility.BollingerBands(df["Close"], window=BB_PERIOD, window_dev=BB_STD)
    df["bb_up"]  = bb.bollinger_hband()
    df["bb_lo"]  = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_w"]   = (df["bb_up"] - df["bb_lo"]) / df["bb_mid"]

    last     = df.iloc[-1]
    denom    = (last["bb_up"] - last["bb_lo"])
    pct_b    = (last["Close"] - last["bb_lo"]) / denom if denom > 0 else 0.5
    squeeze  = last["bb_w"] < df["bb_w"].quantile(0.15)
    walk_up  = all(df["Close"].iloc[-3:] > df["bb_up"].iloc[-3:])
    walk_dn  = all(df["Close"].iloc[-3:] < df["bb_lo"].iloc[-3:])

    if walk_up:
        return {"signal": "BUY",  "reason": f"Walking upper BB (3 days) — strong momentum", "score": 0.82}
    if walk_dn:
        return {"signal": "SELL", "reason": f"Walking lower BB (3 days) — strong sell pressure", "score": 0.80}
    if pct_b < 0.05:
        r  = f"Price at/below lower BB (pct_b {pct_b:.2f})" + (" + Squeeze!" if squeeze else "")
        sc = 0.88 if squeeze else 0.78
        return {"signal": "BUY",  "reason": r, "score": sc}
    if pct_b > 0.95:
        return {"signal": "SELL", "reason": f"Price at/above upper BB (pct_b {pct_b:.2f})", "score": 0.78}
    if pct_b < 0.20:
        return {"signal": "BUY",  "reason": f"Price near lower BB — mean reversion setup (pct_b {pct_b:.2f})", "score": 0.62}
    if pct_b > 0.80:
        return {"signal": "SELL", "reason": f"Price near upper BB — stretched (pct_b {pct_b:.2f})", "score": 0.60}
    if squeeze:
        return {"signal": "HOLD", "reason": f"BB Squeeze — coiling for breakout (pct_b {pct_b:.2f})", "score": 0.58}
    return {"signal": "HOLD", "reason": f"Price mid-band (pct_b {pct_b:.2f}) — no edge", "score": 0.48}


def breakout_strategy(df: pd.DataFrame, lookback: int = 252) -> dict:
    """52-week high/low breakout with volume and ATR confirmation."""
    if len(df) < lookback + 5:
        return _base_signal()
    recent   = df.tail(lookback)
    last     = df.iloc[-1]
    high_52w = recent["High"].max()
    low_52w  = recent["Low"].min()
    avg_vol  = df["Volume"].rolling(20).mean().iloc[-1]
    vol_ratio = last["Volume"] / avg_vol if avg_vol > 0 else 1.0
    vol_conf  = vol_ratio >= 1.5

    # ATR for relative strength
    atr = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"], window=14).average_true_range().iloc[-1]
    atr_pct = atr / last["Close"] * 100

    pct_from_high = (last["Close"] / high_52w - 1) * 100
    pct_from_low  = (last["Close"] / low_52w  - 1) * 100

    if pct_from_high >= -1.0:   # within 1% of 52W high
        score = 0.92 if vol_conf else 0.62
        signal = "BUY" if vol_conf else "HOLD"
        return {"signal": signal, "reason": f"52W high breakout (vol {vol_ratio:.1f}x avg, ATR {atr_pct:.1f}%)", "score": score}
    if pct_from_high >= -5.0:   # within 5% of 52W high
        return {"signal": "BUY",  "reason": f"Approaching 52W high ({pct_from_high:.1f}%) — watch for breakout", "score": 0.60}
    if pct_from_low <= 2.0:     # within 2% of 52W low
        return {"signal": "SELL", "reason": f"Near 52W low ({pct_from_low:.1f}% above) — breakdown risk", "score": 0.78}
    if pct_from_low <= 10.0:
        return {"signal": "SELL", "reason": f"Weak — only {pct_from_low:.1f}% above 52W low", "score": 0.55}

    return {"signal": "HOLD", "reason": f"Mid-range: {pct_from_high:.1f}% from 52W high, {pct_from_low:.1f}% from low", "score": 0.48}


def volume_spike(df: pd.DataFrame, window: int = 20) -> dict:
    """Volume spike detection with OBV trend and price context."""
    if len(df) < window + 5:
        return _base_signal()

    avg_vol   = df["Volume"].rolling(window).mean().iloc[-1]
    last      = df.iloc[-1]
    prev      = df.iloc[-2]
    ratio     = last["Volume"] / avg_vol if avg_vol > 0 else 1.0
    price_up  = last["Close"] > last["Open"]
    price_chg = (last["Close"] / prev["Close"] - 1) * 100

    # OBV trend (5-day slope)
    df = df.copy()
    df["obv"] = ta.volume.OnBalanceVolumeIndicator(df["Close"], df["Volume"]).on_balance_volume()
    obv_slope = (df["obv"].iloc[-1] - df["obv"].iloc[-6]) / (abs(df["obv"].iloc[-6]) + 1)

    if ratio >= VOLUME_SPIKE_MULTIPLIER * 1.5:  # Very high spike (3x+)
        signal = "BUY" if price_up else "SELL"
        score  = min(0.60 + ratio * 0.06, 0.95)
        return {"signal": signal, "reason": f"Extreme volume spike {ratio:.1f}x avg, price {price_chg:+.1f}%", "score": score}
    if ratio >= VOLUME_SPIKE_MULTIPLIER:
        signal = "BUY" if price_up else "SELL"
        score  = min(0.52 + ratio * 0.06, 0.85)
        return {"signal": signal, "reason": f"Volume spike {ratio:.1f}x avg with {'up' if price_up else 'down'} close", "score": score}
    if obv_slope > 0.05:
        return {"signal": "BUY",  "reason": f"OBV rising (accumulation), vol {ratio:.1f}x avg", "score": 0.58}
    if obv_slope < -0.05:
        return {"signal": "SELL", "reason": f"OBV falling (distribution), vol {ratio:.1f}x avg", "score": 0.55}

    return {"signal": "HOLD", "reason": f"Normal volume ({ratio:.1f}x avg), OBV flat", "score": 0.48}


STRATEGIES = {
    "EMA Crossover":   ema_crossover,
    "RSI + MACD":      rsi_macd,
    "Bollinger Bands": bollinger_bands,
    "Breakout":        breakout_strategy,
    "Volume Spike":    volume_spike,
}


def run_all_strategies(df: pd.DataFrame) -> dict:
    """Run all strategies independently and return full results dict."""
    return {name: func(df) for name, func in STRATEGIES.items()}


def get_consensus(results: dict) -> dict:
    """
    Weighted consensus — vote counting (60%) + score weighting (40%).
    Threshold = 0.38 (2 agreeing strategies out of 5 is actionable).
    No all-HOLD default bias.
    """
    buy_votes  = sum(1 for v in results.values() if v["signal"] == "BUY")
    sell_votes = sum(1 for v in results.values() if v["signal"] == "SELL")
    n = len(results)

    buy_score  = sum(v["score"] for v in results.values() if v["signal"] == "BUY")
    sell_score = sum(v["score"] for v in results.values() if v["signal"] == "SELL")
    total_score = sum(v["score"] for v in results.values())

    buy_wpct  = (buy_score  / total_score) if total_score > 0 else 0
    sell_wpct = (sell_score / total_score) if total_score > 0 else 0
    buy_vpct  = buy_votes  / n if n > 0 else 0
    sell_vpct = sell_votes / n if n > 0 else 0

    buy_combined  = 0.6 * buy_vpct  + 0.4 * buy_wpct
    sell_combined = 0.6 * sell_vpct + 0.4 * sell_wpct

    buy_reasons  = [v["reason"][:50] for v in results.values() if v["signal"] == "BUY"]
    sell_reasons = [v["reason"][:50] for v in results.values() if v["signal"] == "SELL"]

    if buy_combined >= 0.38 and buy_combined > sell_combined:
        conf = min(round(buy_combined * 1.25, 3), 0.99)
        return {
            "signal": "BUY",
            "confidence": conf,
            "buy_pct": round(buy_vpct * 100),
            "sell_pct": round(sell_vpct * 100),
            "agreeing_strategies": buy_votes,
            "reason_summary": " | ".join(buy_reasons[:2]),
        }
    elif sell_combined >= 0.38 and sell_combined > buy_combined:
        conf = min(round(sell_combined * 1.25, 3), 0.99)
        return {
            "signal": "SELL",
            "confidence": conf,
            "buy_pct": round(buy_vpct * 100),
            "sell_pct": round(sell_vpct * 100),
            "agreeing_strategies": sell_votes,
            "reason_summary": " | ".join(sell_reasons[:2]),
        }
    else:
        dominant = "bullish lean" if buy_combined > sell_combined else \
                   "bearish lean" if sell_combined > buy_combined else "neutral"
        return {
            "signal": "HOLD",
            "confidence": max(round(1.0 - max(buy_combined, sell_combined), 3), 0.35),
            "buy_pct": round(buy_vpct * 100),
            "sell_pct": round(sell_vpct * 100),
            "agreeing_strategies": 0,
            "reason_summary": f"Mixed — {dominant} ({buy_votes} buy, {sell_votes} sell of {n})",
        }


def deep_analysis(df: pd.DataFrame) -> dict:
    """
    Deep research mode: trend alignment, momentum, volatility, support/resistance.
    Returns context used to adjust confidence and generate richer reasoning.
    """
    if df is None or len(df) < 60:
        return {"data_quality": "INSUFFICIENT", "years": 0}

    years  = round(len(df) / 252, 1)
    close  = df["Close"]
    ema20  = close.ewm(span=20).mean()
    ema50  = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()
    lc     = close.iloc[-1]

    short_trend = "UP" if lc > ema20.iloc[-1]  else "DOWN"
    mid_trend   = "UP" if lc > ema50.iloc[-1]  else "DOWN"
    long_trend  = "UP" if lc > ema200.iloc[-1] else "DOWN"
    aligned     = (short_trend == mid_trend == long_trend)

    roc14   = (close.iloc[-1] / close.iloc[-15] - 1) * 100 if len(close) > 15 else 0
    vol_ann = close.pct_change().dropna().tail(20).std() * (252 ** 0.5) * 100

    high_52 = df["High"].tail(252).max()
    low_52  = df["Low"].tail(252).min()

    dq = "POOR" if years < 3 else "LOW" if years < 5 else "MODERATE" if years < 8 else "GOOD"

    return {
        "years": years,
        "data_quality": dq,
        "short_trend": short_trend,
        "mid_trend":   mid_trend,
        "long_trend":  long_trend,
        "trend_aligned": aligned,
        "trend_dir":   long_trend,
        "momentum_roc14": round(roc14, 2),
        "annualised_vol":  round(vol_ann, 1),
        "pct_from_52w_high": round((lc / high_52 - 1) * 100, 1),
        "pct_from_52w_low":  round((lc / low_52  - 1) * 100, 1),
    }


def check_signal_bias(signals: list) -> dict:
    """
    Validate batch signal distribution.
    Flag if >80% are HOLD — likely a stale-data or model issue.
    """
    if not signals:
        return {"bias": False, "message": ""}
    total      = len(signals)
    hold_count = sum(1 for s in signals if s.get("signal") == "HOLD")
    buy_count  = sum(1 for s in signals if s.get("signal") == "BUY")
    sell_count = sum(1 for s in signals if s.get("signal") == "SELL")
    hold_pct   = hold_count / total * 100

    if hold_pct > 80:
        return {
            "bias": True,
            "message": (
                f"⚠ Signal bias detected: {hold_pct:.0f}% HOLD across {total} stocks "
                f"({buy_count} BUY, {sell_count} SELL). "
                "Market may be in consolidation, or data freshness should be checked."
            ),
        }
    return {"bias": False, "message": "", "buy": buy_count, "sell": sell_count, "hold": hold_count}
