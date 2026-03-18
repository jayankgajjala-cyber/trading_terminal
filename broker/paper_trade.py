"""
broker/paper_trade.py — Simulated paper trading engine.
Tracks virtual portfolio, P&L, and budget allocation.
"""
import pandas as pd
from data.cache import CacheManager
from data.fetcher import get_historical_data
from config.settings import DEFAULT_MONTHLY_BUDGET

cache = CacheManager()


class PaperTrader:
    def __init__(self, initial_cash: float = 100000.0):
        self.initial_cash = initial_cash

    def buy(self, symbol: str, amount_inr: float) -> dict:
        """Buy as many shares as amount_inr allows at current price."""
        df = get_historical_data(symbol, period="5d")
        if df.empty:
            return {"success": False, "message": "Could not fetch price"}
        price = round(df["Close"].iloc[-1], 2)
        qty = int(amount_inr // price)
        if qty == 0:
            return {"success": False, "message": f"Amount ₹{amount_inr} too small for ₹{price}"}
        cache.record_paper_trade(symbol, "BUY", qty, price)
        return {
            "success": True,
            "symbol": symbol,
            "action": "BUY",
            "quantity": qty,
            "price": price,
            "invested": round(qty * price, 2),
            "message": f"Bought {qty} shares @ ₹{price:,.2f}"
        }

    def sell(self, symbol: str, qty: int = None) -> dict:
        """Sell qty shares (or full holding if qty=None)."""
        portfolio = cache.get_paper_portfolio()
        holding = portfolio[portfolio["symbol"] == symbol]
        if holding.empty:
            return {"success": False, "message": f"No position in {symbol}"}
        held_qty = int(holding.iloc[0]["quantity"])
        sell_qty = qty or held_qty
        if sell_qty > held_qty:
            return {"success": False, "message": f"Only {held_qty} shares held"}

        df = get_historical_data(symbol, period="5d")
        if df.empty:
            return {"success": False, "message": "Could not fetch price"}
        price = round(df["Close"].iloc[-1], 2)
        avg_price = float(holding.iloc[0]["avg_price"])
        pnl = round((price - avg_price) * sell_qty, 2)
        cache.record_paper_trade(symbol, "SELL", sell_qty, price)
        return {
            "success": True,
            "symbol": symbol,
            "action": "SELL",
            "quantity": sell_qty,
            "price": price,
            "pnl": pnl,
            "pnl_pct": round((price - avg_price) / avg_price * 100, 2),
            "message": f"Sold {sell_qty} shares @ ₹{price:,.2f} | P&L: ₹{pnl:+,.2f}"
        }

    def get_portfolio_summary(self) -> pd.DataFrame:
        """Return portfolio with current prices and P&L."""
        portfolio = cache.get_paper_portfolio()
        if portfolio.empty:
            return pd.DataFrame()
        rows = []
        for _, row in portfolio.iterrows():
            sym = row["symbol"]
            df = get_historical_data(sym, period="5d")
            cmp = round(df["Close"].iloc[-1], 2) if not df.empty else row["avg_price"]
            qty = int(row["quantity"])
            avg = float(row["avg_price"])
            invested = round(qty * avg, 2)
            current_val = round(qty * cmp, 2)
            pnl = round(current_val - invested, 2)
            pnl_pct = round(pnl / invested * 100, 2) if invested > 0 else 0
            rows.append({
                "Symbol": sym, "Qty": qty, "Avg Price": avg,
                "CMP": cmp, "Invested": invested,
                "Current Value": current_val,
                "P&L": pnl, "P&L %": pnl_pct
            })
        return pd.DataFrame(rows)

    def suggest_allocation(self, budget: float = None, symbols: list[str] = None,
                           signals: list[dict] = None) -> pd.DataFrame:
        """
        Suggest how to allocate monthly budget across BUY signals.
        Equal-weighted by default; higher confidence = more weight.
        """
        budget = budget or DEFAULT_MONTHLY_BUDGET
        buy_signals = [s for s in (signals or []) if s["signal"] == "BUY"]
        if not buy_signals:
            return pd.DataFrame(columns=["Symbol", "Allocation", "Approx Shares", "Signal Confidence"])

        total_conf = sum(s.get("confidence", 0.5) for s in buy_signals)
        rows = []
        for s in buy_signals:
            weight = s.get("confidence", 0.5) / total_conf
            alloc = round(budget * weight, 0)
            df = get_historical_data(s["symbol"], period="5d")
            price = round(df["Close"].iloc[-1], 2) if not df.empty else 0
            shares = int(alloc // price) if price > 0 else 0
            rows.append({
                "Symbol": s["symbol"],
                "Allocation (₹)": alloc,
                "~Shares": shares,
                "Price": price,
                "Confidence": f"{s.get('confidence', 0)*100:.0f}%"
            })
        return pd.DataFrame(rows)
