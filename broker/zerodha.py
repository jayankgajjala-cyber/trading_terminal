"""
broker/zerodha.py — Zerodha Kite Connect integration.
Handles session, holdings, positions, orders, live prices.
Falls back to yfinance if not connected.
"""
import os
import json
import time
import logging
from pathlib import Path
import pandas as pd
import yfinance as yf
from config.settings import ZERODHA_API_KEY, ZERODHA_API_SECRET, ZERODHA_ACCESS_TOKEN

logger = logging.getLogger(__name__)
TOKEN_FILE = "db/zerodha_token.json"


class ZerodhaClient:
    def __init__(self):
        self.kite = None
        self._connected = False
        self._init_kite()

    def _init_kite(self):
        """Initialize Kite. Gracefully degrades if not configured."""
        if not ZERODHA_API_KEY:
            logger.warning("Zerodha not configured. Using yfinance fallback.")
            return
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=ZERODHA_API_KEY)
            token = self._load_token()
            if token:
                self.kite.set_access_token(token)
                # Quick validation
                self.kite.profile()
                self._connected = True
                logger.info("Zerodha connected via saved token.")
        except Exception as e:
            logger.warning(f"Zerodha init failed: {e}. Will use yfinance.")

    def get_login_url(self) -> str:
        if self.kite:
            return self.kite.login_url()
        return ""

    def generate_session(self, request_token: str) -> bool:
        """Exchange request_token for access_token after OAuth redirect."""
        try:
            from kiteconnect import KiteConnect
            self.kite = KiteConnect(api_key=ZERODHA_API_KEY)
            data = self.kite.generate_session(request_token, api_secret=ZERODHA_API_SECRET)
            self.kite.set_access_token(data["access_token"])
            self._save_token(data["access_token"])
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Session generation failed: {e}")
            return False

    def _save_token(self, token: str):
        Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            json.dump({"access_token": token, "timestamp": time.time()}, f)

    def _load_token(self) -> str | None:
        try:
            with open(TOKEN_FILE) as f:
                data = json.load(f)
            # Tokens valid for 1 day (86400 seconds)
            if time.time() - data["timestamp"] < 86000:
                return data["access_token"]
        except Exception:
            pass
        return None

    @property
    def connected(self) -> bool:
        return self._connected

    # ─── Portfolio Data ──────────────────────────────────────────────────────

    def get_holdings(self) -> pd.DataFrame:
        """Return holdings as DataFrame. Falls back to empty DF."""
        if self._connected:
            try:
                holdings = self.kite.holdings()
                return pd.DataFrame(holdings)
            except Exception as e:
                logger.error(f"Holdings fetch failed: {e}")
        return pd.DataFrame()

    def get_positions(self) -> dict:
        """Return day + net positions."""
        if self._connected:
            try:
                return self.kite.positions()
            except Exception as e:
                logger.error(f"Positions fetch failed: {e}")
        return {"day": [], "net": []}

    def get_orders(self) -> pd.DataFrame:
        if self._connected:
            try:
                orders = self.kite.orders()
                return pd.DataFrame(orders)
            except Exception as e:
                logger.error(f"Orders fetch failed: {e}")
        return pd.DataFrame()

    def get_live_price(self, instruments: list[str]) -> dict:
        """
        Fetch live LTP for a list of Zerodha instrument tokens/symbols.
        Falls back to yfinance last close if not connected.
        """
        if self._connected:
            try:
                return self.kite.ltp(instruments)
            except Exception as e:
                logger.warning(f"LTP fetch failed: {e}. Using yfinance.")
        return self._yfinance_prices(instruments)

    def _yfinance_prices(self, symbols: list[str]) -> dict:
        """Convert NSE symbols to Yahoo suffix and fetch last price."""
        result = {}
        for sym in symbols:
            yf_sym = sym if sym.endswith(".NS") else f"{sym}.NS"
            try:
                ticker = yf.Ticker(yf_sym)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    result[sym] = {"last_price": round(hist["Close"].iloc[-1], 2)}
            except Exception:
                result[sym] = {"last_price": 0}
        return result

    def place_order(self, tradingsymbol: str, exchange: str, transaction_type: str,
                    quantity: int, order_type: str = "MARKET",
                    product: str = "CNC") -> str | None:
        """Place a real order. Returns order_id or None."""
        if not self._connected:
            logger.warning("Not connected to Zerodha. Order not placed.")
            return None
        try:
            from kiteconnect import KiteConnect
            order_id = self.kite.place_order(
                variety=KiteConnect.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=product,
                order_type=order_type
            )
            return order_id
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return None


# Singleton
_client = None

def get_client() -> ZerodhaClient:
    global _client
    if _client is None:
        _client = ZerodhaClient()
    return _client
