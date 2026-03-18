# 📈 Trading Terminal

> Private AI-powered stock portfolio intelligence system for Zerodha users.  
> Built with Streamlit · 100% free infrastructure · Dark terminal UI

---

## Features

- **Portfolio Overview** — Live holdings, P&L, allocation charts, budget planner
- **Strategy Signals** — Real-time BUY/SELL/HOLD signals across 5 technical strategies
- **Backtesting** — Backtrader-powered historical testing with CAGR, Sharpe, Max DD
- **News Feed** — Portfolio-specific + Nifty 50 + global macro news
- **Paper Trading** — Simulated orders with live yfinance prices and P&L tracking
- **Stock Search** — Full analysis for any NSE stock: chart, fundamentals, predictions
- **Zerodha Connect** — Live portfolio sync via Kite Connect API
- **Email Alerts** — Gmail SMTP alerts on signal changes + OTP login

## Security

- Username + Password + OTP (email) — 3-factor authentication
- No public access without OTP verification
- All secrets stored in Streamlit Cloud Secrets (never in code)

## Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for full instructions.

**Quick start (Streamlit Cloud):**
1. Fork this repo
2. Connect to [share.streamlit.io](https://share.streamlit.io)
3. Add secrets in App Settings → Secrets
4. Deploy

## Tech Stack

| Layer | Tool |
|---|---|
| UI | Streamlit |
| Data | yfinance, Alpha Vantage, Google News RSS |
| Broker | Zerodha Kite Connect |
| Backtesting | Backtrader |
| Scheduling | APScheduler |
| Charts | Plotly |
| Database | SQLite + Parquet |
| Auth | bcrypt + OTP via Gmail |
| Alerts | Gmail SMTP |

---

*Not financial advice. For personal use only.*
