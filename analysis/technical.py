"""
analysis/technical.py — All technical strategies.
Returns signal dict: {"signal": "BUY"/"SELL"/"HOLD", "reason": str, "score": float}
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
    """Golden Cross / Death Cross on 50/200 EMA."""
    if len(df) < EMA_LONG + 5:
        return _base_signal()
    df = df.copy()
    df["ema_short"] = df["Close"].ewm(span=EMA_SHORT, adjust=False).mean()
    df["ema_long"] = df["Close"].ewm(span=EMA_LONG, adjust=False).mean()
    last = df.iloc[-1]
    prev = df.iloc[-2]
    cross_up = prev["ema_short"] <= prev["ema_long"] and last["ema_short"] > last["ema_long"]
    cross_down = prev["ema_short"] >= prev["ema_long"] and last["ema_short"] < last["ema_long"]
    above = last["ema_short"] > last["ema_long"]
    gap_pct = abs(last["ema_short"] - last["ema_long"]) / last["ema_long"] * 100

    if cross_up:
        return {"signal": "BUY", "reason": "Golden Cross (50 EMA crossed above 200 EMA)", "score": 0.9}
    if cross_down:
        return {"signal": "SELL", "reason": "Death Cross (50 EMA crossed below 200 EMA)", "score": 0.9}
    if above:
        return {"signal": "HOLD", "reason": f"Bullish trend (gap: {gap_pct:.1f}%)", "score": 0.6}
    return {"signal": "HOLD", "reason": f"Bearish trend (gap: {gap_pct:.1f}%)", "score": 0.4}


def rsi_macd(df: pd.DataFrame) -> dict:
    """RSI oversold/overbought + MACD histogram cross."""
    if len(df) < MACD_SLOW + MACD_SIGNAL + 5:
        return _base_signal()
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(df["Close"], window=RSI_PERIOD).rsi()
    macd = ta.trend.MACD(df["Close"], window_fast=MACD_FAST,
                          window_slow=MACD_SLOW, window_sign=MACD_SIGNAL)
    df["macd_hist"] = macd.macd_diff()
    df["macd_line"] = macd.macd()
    df["signal_line"] = macd.macd_signal()

    r = df.iloc[-1]["rsi"]
    hist = df.iloc[-1]["macd_hist"]
    prev_hist = df.iloc[-2]["macd_hist"]
    macd_cross_up = prev_hist < 0 and hist > 0
    macd_cross_down = prev_hist > 0 and hist < 0

    reasons = []
    score = 0.5
    signal = "HOLD"

    if r < RSI_OVERSOLD:
        reasons.append(f"RSI oversold ({r:.1f})")
        score += 0.2
        signal = "BUY"
    elif r > RSI_OVERBOUGHT:
        reasons.append(f"RSI overbought ({r:.1f})")
        score += 0.2
        signal = "SELL"

    if macd_cross_up:
        reasons.append("MACD bullish cross")
        score = min(score + 0.3, 1.0)
        signal = "BUY"
    elif macd_cross_down:
        reasons.append("MACD bearish cross")
        score = min(score + 0.3, 1.0)
        signal = "SELL"

    return {"signal": signal, "reason": " | ".join(reasons) or "RSI/MACD neutral", "score": score}


def bollinger_bands(df: pd.DataFrame) -> dict:
    """Price touching lower/upper band with squeeze detection."""
    if len(df) < BB_PERIOD + 5:
        return _base_signal()
    df = df.copy()
    bb = ta.volatility.BollingerBands(df["Close"], window=BB_PERIOD, window_dev=BB_STD)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()
    df["bb_mid"] = bb.bollinger_mavg()
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]

    last = df.iloc[-1]
    pct_b = (last["Close"] - last["bb_lower"]) / (last["bb_upper"] - last["bb_lower"])
    squeeze = last["bb_width"] < df["bb_width"].quantile(0.2)

    if pct_b < 0.05:
        s = "BUY"
        r = f"Price at lower BB (pct_b: {pct_b:.2f})" + (" | Squeeze!" if squeeze else "")
        sc = 0.85
    elif pct_b > 0.95:
        s = "SELL"
        r = f"Price at upper BB (pct_b: {pct_b:.2f})"
        sc = 0.80
    elif squeeze:
        s = "HOLD"
        r = f"BB Squeeze — breakout imminent (pct_b: {pct_b:.2f})"
        sc = 0.6
    else:
        s = "HOLD"
        r = f"Price within BB (pct_b: {pct_b:.2f})"
        sc = 0.5

    return {"signal": s, "reason": r, "score": sc}


def breakout_strategy(df: pd.DataFrame, lookback: int = 52) -> dict:
    """52-week high breakout with volume confirmation."""
    if len(df) < lookback + 5:
        return _base_signal()
    recent = df.iloc[-lookback:]
    last = df.iloc[-1]
    high_52w = recent["High"].max()
    low_52w = recent["Low"].min()
    avg_vol = df["Volume"].rolling(20).mean().iloc[-1]
    vol_spike = last["Volume"] > avg_vol * 1.5

    if last["Close"] >= high_52w * 0.99:
        s = "BUY" if vol_spike else "HOLD"
        r = f"Near 52W high breakout ({last['Close']:.0f} vs {high_52w:.0f})" + \
            (" + Volume spike!" if vol_spike else " — Low volume")
        sc = 0.9 if vol_spike else 0.6
    elif last["Close"] <= low_52w * 1.01:
        s = "SELL"
        r = f"Near 52W low ({last['Close']:.0f} vs {low_52w:.0f})"
        sc = 0.75
    else:
        s = "HOLD"
        r = f"No breakout (52W H: {high_52w:.0f}, L: {low_52w:.0f})"
        sc = 0.5

    return {"signal": s, "reason": r, "score": sc}


def volume_spike(df: pd.DataFrame, window: int = 20) -> dict:
    """Unusual volume detection with price direction context."""
    if len(df) < window + 5:
        return _base_signal()
    avg_vol = df["Volume"].rolling(window).mean().iloc[-1]
    last = df.iloc[-1]
    ratio = last["Volume"] / avg_vol
    price_up = last["Close"] > last["Open"]

    if ratio >= VOLUME_SPIKE_MULTIPLIER:
        s = "BUY" if price_up else "SELL"
        r = f"Volume spike {ratio:.1f}x avg with {'up' if price_up else 'down'} move"
        sc = min(0.5 + ratio * 0.1, 0.95)
    else:
        s = "HOLD"
        r = f"Normal volume ({ratio:.1f}x avg)"
        sc = 0.5

    return {"signal": s, "reason": r, "score": sc}


STRATEGIES = {
    "EMA Crossover": ema_crossover,
    "RSI + MACD": rsi_macd,
    "Bollinger Bands": bollinger_bands,
    "Breakout": breakout_strategy,
    "Volume Spike": volume_spike,
}


def run_all_strategies(df: pd.DataFrame) -> dict[str, dict]:
    """Run all strategies and return results dict keyed by strategy name."""
    return {name: func(df) for name, func in STRATEGIES.items()}


def get_consensus(results: dict[str, dict]) -> dict:
    """
    Weighted consensus across all strategy signals.
    Returns overall signal + confidence.
    """
    buy_score = sum(v["score"] for v in results.values() if v["signal"] == "BUY")
    sell_score = sum(v["score"] for v in results.values() if v["signal"] == "SELL")
    total = sum(v["score"] for v in results.values())

    if total == 0:
        return {"signal": "HOLD", "confidence": 0.0, "buy_pct": 0, "sell_pct": 0}

    buy_pct = buy_score / total
    sell_pct = sell_score / total

    if buy_pct > 0.55:
        return {"signal": "BUY", "confidence": round(buy_pct, 3),
                "buy_pct": round(buy_pct * 100), "sell_pct": round(sell_pct * 100)}
    elif sell_pct > 0.55:
        return {"signal": "SELL", "confidence": round(sell_pct, 3),
                "buy_pct": round(buy_pct * 100), "sell_pct": round(sell_pct * 100)}
    else:
        return {"signal": "HOLD", "confidence": round(max(buy_pct, sell_pct), 3),
                "buy_pct": round(buy_pct * 100), "sell_pct": round(sell_pct * 100)}
