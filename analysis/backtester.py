"""
analysis/backtester.py — Validated backtesting engine.
Fixed: proper diagnostics, no fake metrics, no random strategy selection,
initial capital ₹10,000 tracked, trade count validation.
"""
import logging
import numpy as np
import pandas as pd
import backtrader as bt
import backtrader.analyzers as btanalyzers
from data.cache import CacheManager

logger = logging.getLogger(__name__)
cache  = CacheManager()

INITIAL_CAPITAL = 10000.0   # ₹10,000 as specified


class EMAcrossoverStrategy(bt.Strategy):
    params = (("short", 50), ("long", 200),)
    def __init__(self):
        self.ema_short  = bt.ind.EMA(period=self.p.short)
        self.ema_long   = bt.ind.EMA(period=self.p.long)
        self.crossover  = bt.ind.CrossOver(self.ema_short, self.ema_long)
    def next(self):
        if not self.position:
            if self.crossover > 0: self.buy()
        elif self.crossover < 0:   self.sell()


class RSIMACDStrategy(bt.Strategy):
    params = (("rsi_period", 14), ("macd_fast", 12), ("macd_slow", 26), ("macd_sig", 9),)
    def __init__(self):
        self.rsi        = bt.ind.RSI(period=self.p.rsi_period)
        macd            = bt.ind.MACD(period_me1=self.p.macd_fast,
                                       period_me2=self.p.macd_slow,
                                       period_signal=self.p.macd_sig)
        self.macd_cross = bt.ind.CrossOver(macd.macd, macd.signal)
    def next(self):
        if not self.position:
            if self.rsi < 35 and self.macd_cross > 0: self.buy()
        else:
            if self.rsi > 65 and self.macd_cross < 0: self.sell()


class BollingerStrategy(bt.Strategy):
    params = (("period", 20), ("devfactor", 2),)
    def __init__(self):
        self.bb = bt.ind.BollingerBands(period=self.p.period, devfactor=self.p.devfactor)
    def next(self):
        if not self.position:
            if self.data.close < self.bb.lines.bot: self.buy()
        elif self.data.close > self.bb.lines.top:   self.sell()


class BreakoutStrategy(bt.Strategy):
    params = (("lookback", 260),)
    def __init__(self):
        self.highest = bt.ind.Highest(self.data.high, period=self.p.lookback)
        self.vol_ma  = bt.ind.SMA(self.data.volume, period=20)
    def next(self):
        if not self.position:
            if (self.data.close >= self.highest[-1] * 0.99 and
                    self.data.volume > self.vol_ma * 1.5): self.buy()
        elif self.data.close < self.highest[-1] * 0.92:   self.sell()


class VolumeSpikeStrategy(bt.Strategy):
    params = (("vol_window", 20), ("spike_mult", 2.0),)
    def __init__(self):
        self.vol_ma = bt.ind.SMA(self.data.volume, period=self.p.vol_window)
    def next(self):
        ratio = self.data.volume[0] / self.vol_ma[0]
        if not self.position:
            if ratio >= self.p.spike_mult and self.data.close > self.data.open: self.buy()
        elif ratio >= self.p.spike_mult and self.data.close < self.data.open:   self.sell()


STRATEGY_MAP = {
    "EMA Crossover":   EMAcrossoverStrategy,
    "RSI + MACD":      RSIMACDStrategy,
    "Bollinger Bands": BollingerStrategy,
    "Breakout":        BreakoutStrategy,
    "Volume Spike":    VolumeSpikeStrategy,
}


def validate_metrics(metrics: dict, strategy_name: str) -> dict:
    """
    Validate backtest output. Replace misleading values with honest diagnostics.
    Never let 0 trades show a non-zero CAGR.
    """
    m = metrics.copy()
    diags = []

    total_trades = m.get("total_trades", 0)
    cagr         = m.get("cagr", 0.0)
    sharpe       = m.get("sharpe", 0.0)
    win_rate     = m.get("win_rate", 0.0)
    final_val    = m.get("final_value", INITIAL_CAPITAL)

    # No trades → CAGR is meaningless
    if total_trades == 0:
        m["cagr"]        = 0.0
        m["sharpe"]      = 0.0
        m["win_rate"]    = 0.0
        m["reliability"] = "NO_TRADES"
        diags.append("No trades executed — CAGR not meaningful")

    # Suspiciously low trade count
    elif total_trades < 5:
        m["reliability"] = "VERY_LOW_CONFIDENCE"
        diags.append(f"Only {total_trades} trades — statistically insufficient")

    elif total_trades < 10:
        m["reliability"] = "LOW_CONFIDENCE"
        diags.append(f"{total_trades} trades — low statistical confidence")

    else:
        m["reliability"] = "VALID"

    # Unrealistic Sharpe
    if abs(sharpe) > 10:
        m["sharpe"]  = 0.0
        diags.append(f"Sharpe {sharpe:.1f} unrealistic — set to 0")

    # Final value sanity (shouldn't be below 10% of start or above 1000x)
    if final_val < INITIAL_CAPITAL * 0.05:
        diags.append(f"Final value ₹{final_val:.0f} extremely low — likely data issue")
    if final_val > INITIAL_CAPITAL * 500:
        diags.append(f"Final value ₹{final_val:.0f} unrealistically high")

    # Win rate vs profitability mismatch
    if win_rate > 60 and cagr < 0:
        diags.append(f"Win rate {win_rate:.0f}% high but CAGR negative — losers larger than winners")

    m["diagnostics"]   = diags
    m["initial_capital"] = INITIAL_CAPITAL
    m["strategy"]      = strategy_name
    return m


def run_backtest(df: pd.DataFrame, strategy_name: str) -> dict:
    """Run a single strategy backtest. Returns validated metrics."""
    if df is None or df.empty or len(df) < 252:
        m = _empty_metrics()
        m["strategy"]    = strategy_name
        m["diagnostics"] = ["Insufficient data — need at least 1 year (252 bars)"]
        m["reliability"] = "INSUFFICIENT_DATA"
        return m

    StratClass = STRATEGY_MAP.get(strategy_name)
    if not StratClass:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    cerebro = bt.Cerebro(stdstats=False)
    cerebro.broker.setcash(INITIAL_CAPITAL)
    cerebro.broker.setcommission(commission=0.001)  # 0.1% round-trip

    cerebro.adddata(bt.feeds.PandasData(dataname=df))
    cerebro.addstrategy(StratClass)
    cerebro.addanalyzer(btanalyzers.SharpeRatio, _name="sharpe", riskfreerate=0.065)
    cerebro.addanalyzer(btanalyzers.DrawDown,    _name="drawdown")
    cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name="trades")

    try:
        results    = cerebro.run()
        strat      = results[0]
        final_val  = cerebro.broker.getvalue()
        years      = len(df) / 252
        cagr       = ((final_val / INITIAL_CAPITAL) ** (1.0 / max(years, 0.5)) - 1) * 100

        sharpe_raw = strat.analyzers.sharpe.get_analysis()
        sharpe     = sharpe_raw.get("sharperatio") or 0.0

        dd         = strat.analyzers.drawdown.get_analysis()
        max_dd     = dd.get("max", {}).get("drawdown", 0.0)

        ta_res     = strat.analyzers.trades.get_analysis()
        total_t    = ta_res.get("total", {}).get("total", 0)
        won        = ta_res.get("won",   {}).get("total", 0)
        win_rate   = (won / total_t * 100) if total_t > 0 else 0.0

        raw = {
            "cagr":          round(cagr, 2),
            "sharpe":        round(float(sharpe) if sharpe else 0.0, 3),
            "max_drawdown":  round(max_dd, 2),
            "win_rate":      round(win_rate, 1),
            "total_trades":  total_t,
            "final_value":   round(final_val, 2),
            "strategy":      strategy_name,
        }
        return validate_metrics(raw, strategy_name)

    except Exception as e:
        logger.error(f"Backtest run failed ({strategy_name}): {e}")
        m = _empty_metrics()
        m["strategy"]    = strategy_name
        m["diagnostics"] = [f"Runtime error: {str(e)[:80]}"]
        m["reliability"] = "ERROR"
        return m


def _empty_metrics() -> dict:
    return {
        "cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
        "win_rate": 0.0, "total_trades": 0,
        "final_value": INITIAL_CAPITAL,
        "reliability": "NO_DATA",
        "diagnostics": [],
        "initial_capital": INITIAL_CAPITAL,
    }


def run_all_backtests(symbol: str, df: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    """Run all 5 strategies. Uses cache unless force=True."""
    if not force:
        cached = cache.load_backtest(symbol)
        if not cached.empty:
            # Add missing columns for backwards compatibility
            for col in ["reliability", "diagnostics", "initial_capital"]:
                if col not in cached.columns:
                    cached[col] = ""
            logger.info(f"Using cached backtest for {symbol}")
            return cached

    rows = []
    for name in STRATEGY_MAP:
        logger.info(f"Backtesting {symbol} — {name}")
        m = run_backtest(df, name)
        m["symbol"] = symbol
        cache.save_backtest(symbol, name, m)
        rows.append(m)

    return pd.DataFrame(rows)


def get_best_strategy(results_df: pd.DataFrame) -> tuple:
    """
    Rank strategies by composite score.
    Only consider VALID results (reliability == 'VALID').
    Falls back to best available if none are valid.
    Returns (strategy_name, score, is_reliable).
    """
    if results_df is None or results_df.empty:
        return "EMA Crossover", 0.0, False

    df = results_df.copy()

    # Prefer valid strategies
    valid = df[df.get("reliability", pd.Series([""] * len(df))) == "VALID"] \
            if "reliability" in df.columns else df

    pool = valid if not valid.empty else df

    # Composite score: CAGR × 0.4 + Sharpe × 20 - MaxDD × 0.3 + WinRate × 0.3
    # Penalise strategies with zero trades
    trade_penalty = pool.get("total_trades", pd.Series([0] * len(pool))).apply(
        lambda t: 0 if t >= 10 else -20 if t == 0 else -10
    )
    pool = pool.copy()
    pool["composite"] = (
        pool["cagr"]         * 0.40
        + pool["sharpe"].fillna(0) * 20
        - pool["max_drawdown"] * 0.30
        + pool["win_rate"]   * 0.30
        + trade_penalty
    )

    best_row   = pool.loc[pool["composite"].idxmax()]
    is_reliable = str(best_row.get("reliability", "")) == "VALID"
    return best_row["strategy"], round(best_row["composite"], 3), is_reliable
