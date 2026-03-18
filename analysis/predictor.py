"""
analysis/predictor.py — 12–24 month trend prediction.
Uses EMA slope + optional linear regression on log-prices.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def predict_trend(df: pd.DataFrame, months_ahead: int = 24) -> dict:
    """
    Predict trend using:
    1. EMA slope (fast signal)
    2. Linear regression on log(Close) over last 2 years
    Returns dict with direction, target prices, change percentages.
    """
    if df.empty or len(df) < 60:
        cmp = df["Close"].iloc[-1] if not df.empty else 0
        return {"direction": "HOLD", "target_12m": cmp, "target_24m": cmp,
                "change_pct_12m": 0, "change_pct_24m": 0}

    cmp = df["Close"].iloc[-1]

    # ── EMA Slope Method ─────────────────────────────────────────────────────
    ema_50 = df["Close"].ewm(span=50).mean()
    ema_200 = df["Close"].ewm(span=200).mean()
    slope_50 = (ema_50.iloc[-1] - ema_50.iloc[-20]) / ema_50.iloc[-20]
    slope_200 = (ema_200.iloc[-1] - ema_200.iloc[-60]) / ema_200.iloc[-60]
    bullish_ema = (ema_50.iloc[-1] > ema_200.iloc[-1]) and (slope_50 > 0)

    # ── Linear Regression on Log Prices ──────────────────────────────────────
    lookback = min(504, len(df))  # ~2 years of daily data
    recent = df["Close"].tail(lookback).values
    log_prices = np.log(recent)
    X = np.arange(len(log_prices)).reshape(-1, 1)
    model = LinearRegression().fit(X, log_prices)
    daily_log_return = model.coef_[0]
    annual_return = np.exp(daily_log_return * 252) - 1

    # Project forward
    last_x = len(log_prices)
    days_12m = last_x + 252
    days_24m = last_x + 504
    log_target_12m = model.predict([[days_12m]])[0]
    log_target_24m = model.predict([[days_24m]])[0]
    target_12m = round(np.exp(log_target_12m), 2)
    target_24m = round(np.exp(log_target_24m), 2)

    # Blend EMA slope bias with regression target
    if bullish_ema and annual_return < 0:
        target_12m = round(cmp * (1 + abs(slope_200) * 2), 2)
        target_24m = round(cmp * (1 + abs(slope_200) * 4), 2)

    change_12m = (target_12m / cmp - 1) * 100
    change_24m = (target_24m / cmp - 1) * 100
    direction = "UP" if change_12m > 3 else "DOWN" if change_12m < -3 else "SIDEWAYS"

    return {
        "direction": direction,
        "target_12m": target_12m,
        "target_24m": target_24m,
        "change_pct_12m": round(change_12m, 2),
        "change_pct_24m": round(change_24m, 2),
        "annual_return_estimate": round(annual_return * 100, 2),
        "ema_bullish": bullish_ema,
    }
