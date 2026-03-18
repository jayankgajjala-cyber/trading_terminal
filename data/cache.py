"""
data/cache.py — Two-tier cache:
  Parquet files for OHLCV DataFrames (fast, columnar)
  SQLite for JSON/metadata/backtest results/paper trades
"""
import os
import json
import time
import logging
import sqlite3
import pandas as pd
from pathlib import Path
from config.settings import CACHE_DIR, DB_PATH

logger = logging.getLogger(__name__)
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


class CacheManager:
    def __init__(self):
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS json_cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,
                cagr REAL,
                sharpe REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                run_at REAL DEFAULT (strftime('%s','now')),
                UNIQUE(symbol, strategy)
            );
            CREATE TABLE IF NOT EXISTS strategy_map (
                symbol TEXT PRIMARY KEY,
                best_strategy TEXT NOT NULL,
                score REAL,
                updated_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS paper_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp REAL DEFAULT (strftime('%s','now')),
                pnl REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS paper_portfolio (
                symbol TEXT PRIMARY KEY,
                quantity INTEGER NOT NULL,
                avg_price REAL NOT NULL,
                invested REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                signal TEXT,
                price REAL,
                strategy TEXT,
                sent_at REAL DEFAULT (strftime('%s','now'))
            );
            """)

    # ─── Parquet OHLCV Cache ─────────────────────────────────────────────────

    def _parquet_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace(":", "_")
        return Path(CACHE_DIR) / f"{safe}.parquet"

    def load(self, key: str, max_age_hours: int = 6) -> pd.DataFrame | None:
        p = self._parquet_path(key)
        if not p.exists():
            return None
        age_hours = (time.time() - p.stat().st_mtime) / 3600
        if age_hours > max_age_hours:
            logger.debug(f"Cache stale: {key} ({age_hours:.1f}h old)")
            return None
        return pd.read_parquet(p)

    def save(self, key: str, df: pd.DataFrame):
        p = self._parquet_path(key)
        df.to_parquet(p, compression="snappy")
        logger.debug(f"Cached parquet: {key}")

    # ─── JSON/Metadata Cache ─────────────────────────────────────────────────

    def load_json(self, key: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM json_cache WHERE key=?", (key,)
            ).fetchone()
        if not row:
            return None
        if time.time() > row[1]:
            return None  # expired
        return json.loads(row[0])

    def save_json(self, key: str, value: dict, ttl_hours: float = 1):
        expires = time.time() + ttl_hours * 3600
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO json_cache VALUES (?,?,?)",
                (key, json.dumps(value), expires)
            )

    # ─── Backtest Results ─────────────────────────────────────────────────────

    def save_backtest(self, symbol: str, strategy: str, metrics: dict):
        with self._conn() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO backtest_results
              (symbol, strategy, cagr, sharpe, max_drawdown, win_rate, total_trades)
            VALUES (?,?,?,?,?,?,?)
            """, (symbol, strategy,
                  metrics.get("cagr"), metrics.get("sharpe"),
                  metrics.get("max_drawdown"), metrics.get("win_rate"),
                  metrics.get("total_trades")))

    def load_backtest(self, symbol: str) -> pd.DataFrame:
        with self._conn() as conn:
            return pd.read_sql(
                "SELECT * FROM backtest_results WHERE symbol=? ORDER BY cagr DESC",
                conn, params=(symbol,)
            )

    def save_strategy_map(self, symbol: str, best_strategy: str, score: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO strategy_map VALUES (?,?,?,strftime('%s','now'))",
                (symbol, best_strategy, score)
            )

    def get_best_strategy(self, symbol: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT best_strategy FROM strategy_map WHERE symbol=?", (symbol,)
            ).fetchone()
        return row[0] if row else None

    # ─── Paper Trades ─────────────────────────────────────────────────────────

    def record_paper_trade(self, symbol: str, action: str, qty: int, price: float):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO paper_trades (symbol, action, quantity, price) VALUES (?,?,?,?)",
                (symbol, action, qty, price)
            )
            # Update portfolio
            if action == "BUY":
                existing = conn.execute(
                    "SELECT quantity, avg_price, invested FROM paper_portfolio WHERE symbol=?",
                    (symbol,)
                ).fetchone()
                if existing:
                    new_qty = existing[0] + qty
                    new_invested = existing[2] + qty * price
                    new_avg = new_invested / new_qty
                    conn.execute(
                        "UPDATE paper_portfolio SET quantity=?, avg_price=?, invested=? WHERE symbol=?",
                        (new_qty, new_avg, new_invested, symbol)
                    )
                else:
                    conn.execute(
                        "INSERT INTO paper_portfolio VALUES (?,?,?,?)",
                        (symbol, qty, price, qty * price)
                    )
            elif action == "SELL":
                conn.execute(
                    "UPDATE paper_portfolio SET quantity=quantity-? WHERE symbol=?",
                    (qty, symbol)
                )
                conn.execute(
                    "DELETE FROM paper_portfolio WHERE symbol=? AND quantity<=0",
                    (symbol,)
                )

    def get_paper_portfolio(self) -> pd.DataFrame:
        with self._conn() as conn:
            return pd.read_sql("SELECT * FROM paper_portfolio", conn)

    def get_paper_trades(self, limit: int = 50) -> pd.DataFrame:
        with self._conn() as conn:
            return pd.read_sql(
                "SELECT * FROM paper_trades ORDER BY timestamp DESC LIMIT ?",
                conn, params=(limit,)
            )

    def log_alert(self, symbol: str, signal: str, price: float, strategy: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO alert_log (symbol, signal, price, strategy) VALUES (?,?,?,?)",
                (symbol, signal, price, strategy)
            )

    def export_to_excel(self, filepath: str = "/tmp/trading_terminal_export.xlsx") -> str:
        """
        Export all key data to a multi-sheet Excel workbook.
        Sheets: Backtest Results, Strategy Map, Paper Portfolio, Trade History, Alert Log
        Returns filepath.
        """
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            # ── Backtest Results ──────────────────────────────────────────────
            with self._conn() as conn:
                bt_df = pd.read_sql(
                    "SELECT symbol, strategy, cagr, sharpe, max_drawdown, win_rate, "
                    "total_trades, run_at FROM backtest_results ORDER BY symbol, cagr DESC",
                    conn)
            if not bt_df.empty:
                bt_df["run_at"] = pd.to_datetime(bt_df["run_at"], unit="s").dt.strftime("%Y-%m-%d %H:%M")
                bt_df.rename(columns={
                    "cagr":"CAGR %","sharpe":"Sharpe","max_drawdown":"Max DD %",
                    "win_rate":"Win Rate %","total_trades":"Trades","run_at":"Run At"
                }, inplace=True)
                bt_df.to_excel(writer, sheet_name="Backtest Results", index=False)

            # ── Strategy Map ──────────────────────────────────────────────────
            with self._conn() as conn:
                sm_df = pd.read_sql(
                    "SELECT symbol, best_strategy, score, updated_at FROM strategy_map ORDER BY symbol",
                    conn)
            if not sm_df.empty:
                sm_df["updated_at"] = pd.to_datetime(sm_df["updated_at"], unit="s").dt.strftime("%Y-%m-%d")
                sm_df.rename(columns={"best_strategy":"Best Strategy","score":"Composite Score",
                                       "updated_at":"Updated"}, inplace=True)
                sm_df.to_excel(writer, sheet_name="Strategy Map", index=False)

            # ── Paper Portfolio ───────────────────────────────────────────────
            paper = self.get_paper_portfolio()
            if not paper.empty:
                paper.to_excel(writer, sheet_name="Paper Portfolio", index=False)

            # ── Trade History ─────────────────────────────────────────────────
            trades = self.get_paper_trades(limit=500)
            if not trades.empty:
                trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s").dt.strftime("%Y-%m-%d %H:%M")
                trades.to_excel(writer, sheet_name="Trade History", index=False)

            # ── Alert Log ─────────────────────────────────────────────────────
            with self._conn() as conn:
                alerts = pd.read_sql(
                    "SELECT symbol, signal, price, strategy, sent_at FROM alert_log "
                    "ORDER BY sent_at DESC LIMIT 200", conn)
            if not alerts.empty:
                alerts["sent_at"] = pd.to_datetime(alerts["sent_at"], unit="s").dt.strftime("%Y-%m-%d %H:%M")
                alerts.to_excel(writer, sheet_name="Alert Log", index=False)

            # ── Style the workbook ────────────────────────────────────────────
            wb = writer.book
            header_fill = PatternFill("solid", fgColor="0A0F1C")
            header_font = Font(color="00D4FF", bold=True, name="Consolas", size=10)
            for sheet in wb.worksheets:
                for cell in sheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center")
                for col in sheet.columns:
                    max_len = max((len(str(cell.value or "")) for cell in col), default=8)
                    sheet.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)

        return filepath
