"""
scheduler_runner.py — APScheduler daemon.
Run this in a separate process alongside Streamlit:
  python scheduler_runner.py

Jobs:
  Every 5 min (market hours): strategy signal checks
  Weekly Monday 8 AM IST: full analysis + backtest
  Daily 8 AM IST: news digest
"""
import logging
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from config.settings import NIFTY50, DEFAULT_MONTHLY_BUDGET
from alerts.signal_engine import check_signals, is_market_hours, scan_nifty500
from alerts.emailer import send_news_digest, send_opportunity_alert
from news.fetcher import fetch_all_news
from data.fetcher import get_bulk_data
from analysis.backtester import run_all_backtests, get_best_strategy
from data.cache import CacheManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("scheduler")
IST = pytz.timezone("Asia/Kolkata")
cache = CacheManager()


def job_signal_check():
    """Every 5 minutes during market hours."""
    if not is_market_hours():
        return
    logger.info("Running 5-min signal check...")
    signals = check_signals(NIFTY50, send_email=True)
    buy_sell = [s for s in signals if s["signal"] in ("BUY", "SELL")]
    logger.info(f"Checked {len(NIFTY50)} stocks, {len(buy_sell)} actionable signals.")


def job_weekly_analysis():
    """Monday 8 AM IST — Full analysis + backtesting for all Nifty 50."""
    logger.info("Starting weekly full analysis...")
    data_map = get_bulk_data(NIFTY50, period="10y")
    for symbol, df in data_map.items():
        if df.empty:
            continue
        logger.info(f"Running backtest: {symbol}")
        results = run_all_backtests(symbol, df, force=True)
        best_strat, score, reliable = get_best_strategy(results)
        cache.save_strategy_map(symbol, best_strat, score)
        logger.info(f"{symbol} → Best: {best_strat} (score: {score})")
    logger.info("Weekly analysis complete.")


def job_nifty500_scan():
    """Weekly scan of broader market for new opportunities."""
    # In production: load full Nifty 500 list; here using Nifty 50 as demo
    logger.info("Running Nifty 500 opportunity scan...")
    signals = scan_nifty500(NIFTY50)
    opps = [s for s in signals if s["signal"] in ("BUY", "SELL") and
            s.get("confidence", 0) > 0.7]
    if opps:
        send_opportunity_alert(opps)
    logger.info(f"Scan found {len(opps)} high-confidence opportunities.")


def job_news_digest():
    """Daily 8 AM IST — Send news digest email."""
    logger.info("Fetching news for digest...")
    articles = fetch_all_news(NIFTY50[:10])
    send_news_digest(articles)


def main():
    scheduler = BlockingScheduler(timezone=IST)

    # Every 5 minutes on weekdays during market hours
    scheduler.add_job(
        job_signal_check,
        CronTrigger(day_of_week="mon-fri", hour="9-15",
                    minute="*/5", timezone=IST),
        id="signal_check",
        max_instances=1,
        misfire_grace_time=60
    )

    # Weekly: Full backtest + analysis (Monday 7 AM IST before market opens)
    scheduler.add_job(
        job_weekly_analysis,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=IST),
        id="weekly_analysis",
        max_instances=1,
        misfire_grace_time=600
    )

    # Weekly: Nifty 500 opportunity scan (Friday 4 PM IST after close)
    scheduler.add_job(
        job_nifty500_scan,
        CronTrigger(day_of_week="fri", hour=16, minute=0, timezone=IST),
        id="nifty500_scan",
        max_instances=1,
        misfire_grace_time=300
    )

    # Daily: News digest (8 AM IST weekdays)
    scheduler.add_job(
        job_news_digest,
        CronTrigger(day_of_week="mon-fri", hour=8, minute=0, timezone=IST),
        id="news_digest",
        max_instances=1,
        misfire_grace_time=300
    )

    logger.info("Scheduler started. Jobs registered:")
    for job in scheduler.get_jobs():
        logger.info(f"  {job.id}: {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
