"""
config/settings.py — Reads from st.secrets (Streamlit Cloud) with .env fallback.
This is the ONLY place secrets are read from.
"""
import os
import streamlit as st


def _get(section: str, key: str, fallback: str = "") -> str:
    """Read from st.secrets first, then env vars, then fallback."""
    try:
        return st.secrets[section][key]
    except (KeyError, AttributeError, FileNotFoundError):
        env_key = f"{section.upper()}_{key.upper()}"
        return os.getenv(env_key, fallback)


# ── Auth
AUTH_USERNAME     = _get("auth", "USERNAME", "Jayank8294")
AUTH_PASSWORD_HASH = _get("auth", "PASSWORD_HASH", "")

# ── Email
OTP_RECIPIENT_EMAIL = _get("email", "OTP_RECIPIENT", "jayankgajjala@gmail.com")

# ── Resend (email delivery)
RESEND_API_KEY  = _get("resend", "API_KEY", "")
RESEND_DOMAIN   = _get("resend", "FROM_DOMAIN", "")

# ── Zerodha
ZERODHA_API_KEY     = _get("zerodha", "API_KEY", "")
ZERODHA_API_SECRET  = _get("zerodha", "API_SECRET", "")
ZERODHA_ACCESS_TOKEN = _get("zerodha", "ACCESS_TOKEN", "")

# ── APIs
ALPHA_VANTAGE_KEY = _get("apis", "ALPHA_VANTAGE_KEY", "demo")
NEWS_API_KEY      = _get("apis", "NEWS_API_KEY", "")

# ── Paths (use /tmp on Streamlit Cloud — ephemeral but fine for cache)
import tempfile, pathlib
_BASE = pathlib.Path(tempfile.gettempdir()) / "trading_terminal"
DB_PATH   = str(_BASE / "trading.db")
CACHE_DIR = str(_BASE / "cache")

# ── Market
MARKET_OPEN_HOUR  = 9;  MARKET_OPEN_MIN  = 15
MARKET_CLOSE_HOUR = 15; MARKET_CLOSE_MIN = 30
DEFAULT_MONTHLY_BUDGET = 15000

# ── Nifty 50
NIFTY50 = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","KOTAKBANK.NS","LT.NS","SBIN.NS","BAJFINANCE.NS",
    "BHARTIARTL.NS","ASIANPAINT.NS","AXISBANK.NS","MARUTI.NS","DMART.NS",
    "TITAN.NS","NESTLEIND.NS","SUNPHARMA.NS","WIPRO.NS","HCLTECH.NS",
    "POWERGRID.NS","TECHM.NS","ONGC.NS","GRASIM.NS","NTPC.NS",
    "ULTRACEMCO.NS","JSWSTEEL.NS","TATASTEEL.NS","INDUSINDBK.NS","ADANIENT.NS",
    "ADANIPORTS.NS","COALINDIA.NS","DRREDDY.NS","APOLLOHOSP.NS","CIPLA.NS",
    "EICHERMOT.NS","BRITANNIA.NS","BPCL.NS","SHREECEM.NS","DIVISLAB.NS",
    "TATACONSUM.NS","BAJAJFINSV.NS","HEROMOTOCO.NS","SBILIFE.NS","HDFCLIFE.NS",
    "HINDALCO.NS","M&M.NS","TATAMOTORS.NS","UPL.NS","ITC.NS",
]

# ── Strategy params
EMA_SHORT=50; EMA_LONG=200; RSI_PERIOD=14
RSI_OVERSOLD=30; RSI_OVERBOUGHT=70
MACD_FAST=12; MACD_SLOW=26; MACD_SIGNAL=9
BB_PERIOD=20; BB_STD=2; VOLUME_SPIKE_MULTIPLIER=2.0
