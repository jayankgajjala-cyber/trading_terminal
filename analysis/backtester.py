"""
analysis/backtester.py — Backtrader-based backtesting for all 5 strategies.
Returns CAGR, Sharpe, Max Drawdown, Win Rate per strategy.
Results cached in SQLite for reuse.
"""
import logging
import numpy as np
import pandas as pd
import backtrader as bt
import backtrader.analyzers as btanalyzers
from data.cache import CacheManager

logger = logging.getLogger(__name__)
cache = CacheManager()


# ─── Strategy Definitions ────────────────────────────────────────────────────

class EMAcrossoverStrategy(bt.Strategy):
    params = (("short", 50), ("long", 200),)

    def __init__(self):
        self.ema_short = bt.ind.EMA(period=self.p.short)
        self.ema_long = bt.ind.EMA(period=self.p.long)
        self.crossover = bt.ind.CrossOver(self.ema_short, self.ema_long)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.sell()


class RSIMACDStrategy(bt.Strategy):
    params = (("rsi_period", 14), ("macd_fast", 12), ("macd_slow", 26), ("macd_sig", 9),)

    def __init__(self):
        self.rsi = bt.ind.RSI(period=self.p.rsi_period)
        macd = bt.ind.MACD(period_me1=self.p.macd_fast, period_me2=self.p.macd_slow,
                           period_signal=self.p.macd_sig)
        self.macd_cross = bt.ind.CrossOver(macd.macd, macd.signal)

    def next(self):
        if not self.position:
            if self.rsi < 35 and self.macd_cross > 0:
                self.buy()
        else:
            if self.rsi > 65 and self.macd_cross < 0:
                self.sell()


class BollingerStrategy(bt.Strategy):
    params = (("period", 20), ("devfactor", 2),)

    def __init__(self):
        self.bb = bt.ind.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)

    def next(self):
        if not self.position:
            if self.data.close < self.bb.lines.bot:
                self.buy()
        elif self.data.close > self.bb.lines.top:
            self.sell()


class BreakoutStrategy(bt.Strategy):
    params = (("lookback", 52 * 5),)  # ~52 weeks in daily bars

    def __init__(self):
        self.highest = bt.ind.Highest(self.data.high, period=self.p.lookback)
        self.vol_ma = bt.ind.SMA(self.data.volume, period=20)

    def next(self):
        if not self.position:
            if (self.data.close >= self.highest[-1] * 0.99 and
                    self.data.volume > self.vol_ma * 1.5):
                self.buy()
        elif self.data.close < self.highest[-1] * 0.92:
            self.sell()


class VolumeSpikeStrategy(bt.Strategy):
    params = (("vol_window", 20), ("spike_mult", 2.0),)

    def __init__(self):
        self.vol_ma = bt.ind.SMA(self.data.volume, period=self.p.vol_window)

    def next(self):
        vol_ratio = self.data.volume[0] / self.vol_ma[0]
        if not self.position:
            if vol_ratio >= self.p.spike_mult and self.data.close > self.data.open:
                self.buy()
        elif vol_ratio >= self.p.spike_mult and self.data.close < self.data.open:
            self.sell()


STRATEGY_MAP = {
    "EMA Crossover": EMAcrossoverStrategy,
    "RSI + MACD": RSIMACDStrategy,
    "Bollinger Bands": BollingerStrategy,
    "Breakout": BreakoutStrategy,
    "Volume Spike": VolumeSpikeStrategy,
}


# ─── Runner ──────────────────────────────────────────────────────────────────

def run_backtest(df: pd.DataFrame, strategy_name: str,
                 initial_cash: float = 100000.0) -> dict:
    """
    Run a single strategy backtest on df (OHLCV DataFrame).
    Returns metrics dict.
    """
    if df.empty or len(df) < 252:
        return _empty_metrics()

    StratClass = STRATEGY_MAP.get(strategy_name)
    if not StratClass:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% (Zerodha ~0.03%, use 0.1% to be safe)

    # Load data
    data_feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data_feed)
    cerebro.addstrategy(StratClass)

    # Analyzers
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name="sharpe", riskfreerate=0.06)
    cerebro.addanalyzer(btanalyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name="trades")
    cerebro.addanalyzer(btanalyzers.Returns, _name="returns")

    results = cerebro.run()
    strat = results[0]

    try:
        final_value = cerebro.broker.getvalue()
        years = len(df) / 252
        cagr = ((final_value / initial_cash) ** (1 / max(years, 1)) - 1) * 100

        sharpe_raw = strat.analyzers.sharpe.get_analysis()
        sharpe = sharpe_raw.get("sharperatio") or 0.0

        dd = strat.analyzers.drawdown.get_analysis()
        max_dd = dd.get("max", {}).get("drawdown", 0.0)

        ta = strat.analyzers.trades.get_analysis()
        total_trades = ta.get("total", {}).get("total", 0)
        won = ta.get("won", {}).get("total", 0)
        win_rate = (won / total_trades * 100) if total_trades > 0 else 0.0

        return {
            "cagr": round(cagr, 2),
            "sharpe": round(sharpe if sharpe else 0.0, 3),
            "max_drawdown": round(max_dd, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": total_trades,
            "final_value": round(final_value, 2),
        }
    except Exception as e:
        logger.error(f"Metric extraction failed: {e}")
        return _empty_metrics()


def _empty_metrics() -> dict:
    return {"cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
            "win_rate": 0.0, "total_trades": 0, "final_value": 0.0}


def run_all_backtests(symbol: str, df: pd.DataFrame,
                      force: bool = False) -> pd.DataFrame:
    """
    Run all strategies for a symbol. Uses cached results unless force=True.
    Returns DataFrame with results.
    """
    if not force:
        cached = cache.load_backtest(symbol)
        if not cached.empty:
            logger.info(f"Using cached backtest for {symbol}")
            return cached

    rows = []
    for name in STRATEGY_MAP:
        logger.info(f"Backtesting {symbol} — {name}")
        metrics = run_backtest(df, name)
        metrics["strategy"] = name
        metrics["symbol"] = symbol
        cache.save_backtest(symbol, name, metrics)
        rows.append(metrics)

    df_results = pd.DataFrame(rows)
    return df_results


def get_best_strategy(results_df: pd.DataFrame) -> tuple[str, float]:
    """
    Composite score = CAGR * 0.4 + Sharpe * 20 - MaxDD * 0.3 + WinRate * 0.3
    Returns (strategy_name, score)
    """
    if results_df.empty:
        return "EMA Crossover", 0.0

    df = results_df.copy()
    df["composite"] = (
        df["cagr"] * 0.4
        + df["sharpe"].fillna(0) * 20
        - df["max_drawdown"] * 0.3
        + df["win_rate"] * 0.3
    )
    best_row = df.loc[df["composite"].idxmax()]
    return best_row["strategy"], round(best_row["composite"], 3)
