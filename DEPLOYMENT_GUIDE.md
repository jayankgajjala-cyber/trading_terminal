# Deployment Guide — Trading Terminal

## Method 1: Streamlit Cloud (Recommended — Free, Always On)

---

### STEP 1 — Generate your password hash (do this FIRST, locally)

Install Python 3.11 and bcrypt, then run:

```bash
pip install bcrypt
python generate_hash.py
```

Copy the output hash — you'll need it in Step 4.

---

### STEP 2 — Push code to GitHub

#### Option A — New repository (easiest)

1. Go to [github.com](https://github.com) → **New repository**
2. Name it: `trading-terminal` (private recommended)
3. Do NOT initialize with README (you already have one)
4. Copy the git commands shown, then in your terminal:

```bash
cd trading_terminal_v2/          # the folder you downloaded and unzipped

git init
git add .
git commit -m "Initial commit — Trading Terminal"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/trading-terminal.git
git push -u origin main
```

#### Option B — Upload via GitHub web UI

1. Create a new repo on GitHub (private)
2. Click **uploading an existing file**
3. Drag-and-drop the entire `trading_terminal_v2` folder contents
4. Commit directly to `main`

> ⚠️ Make sure `.streamlit/secrets.toml` is in `.gitignore` and NOT uploaded.

---

### STEP 3 — Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app**
4. Fill in:
   - **Repository**: `YOUR_USERNAME/trading-terminal`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. Click **Deploy!**

---

### STEP 4 — Add Secrets (CRITICAL — do before first login)

1. In your Streamlit Cloud dashboard, click your app → **⋮ menu → Settings**
2. Click **Secrets** tab
3. Paste the following, filling in your actual values:

```toml
[auth]
USERNAME = "Jayank8294"
PASSWORD_HASH = "PASTE_YOUR_BCRYPT_HASH_FROM_STEP_1_HERE"

[email]
OTP_RECIPIENT = "jayankgajjala@gmail.com"

[resend]
API_KEY = "re_xxxxxxxxxxxxxxxxxxxx"
FROM_DOMAIN = ""     # leave blank initially; set to your domain once verified

[zerodha]
API_KEY = ""
API_SECRET = ""
ACCESS_TOKEN = ""

[apis]
ALPHA_VANTAGE_KEY = ""
NEWS_API_KEY = ""
```

4. Click **Save** — the app restarts automatically.

---

### STEP 5 — Set up Resend (email delivery)

Resend sends your OTPs from randomised addresses on your domain (or their shared domain for free testing).

**Free tier:** 3,000 emails/month, no credit card required.

1. Sign up at [resend.com](https://resend.com)
2. Go to **API Keys** → **Create API Key** (name it `trading-terminal`)
3. Copy the key — it starts with `re_`
4. Add to Streamlit Secrets:

```toml
[resend]
API_KEY = "re_xxxxxxxxxxxxxxxxxxxx"
FROM_DOMAIN = ""     # leave blank for now — explained below
```

**Two sender modes:**

| Mode | Setup | Sender looks like |
|---|---|---|
| **Shared domain** (zero setup) | Leave `FROM_DOMAIN` blank | `onboarding@resend.dev` |
| **Your own domain** | Verify DNS records in Resend dashboard | `alerts-3947@yourdomain.com` |

> For the random-sender effect (different address every OTP), verify your own domain in Resend → DNS settings, then set `FROM_DOMAIN = "yourdomain.com"`. Every OTP will then come from a different random address like `notify-8821@yourdomain.com`, `signals-3047@yourdomain.com`, etc.

> Without a verified domain, the shared domain is used — the sender name still randomises, but the address stays `onboarding@resend.dev`. Fully functional for personal use.

---

### STEP 6 — First Login

1. Open your app URL: `https://your-app-name.streamlit.app`
2. Enter username: `Jayank8294`  
   Enter password: `Jayanju@9498`
3. Click **Send OTP →**
4. Check `jayankgajjala@gmail.com` for the 6-digit OTP
5. Enter OTP → **Verify & Access →**

---

### STEP 7 — Connect Zerodha (Optional)

1. Sign up at [developers.kite.trade](https://developers.kite.trade)
2. Create a new app, set Redirect URL to your Streamlit app URL
3. Add `API_KEY` and `API_SECRET` to Streamlit Secrets
4. In the app → **Zerodha** tab → click **Open Zerodha Login**
5. After login, copy the `request_token` from the redirect URL
6. Paste into the Zerodha tab → **Authenticate**

> Without Zerodha, the app uses yfinance for all price data.

---

## Method 2: Local Machine (Private, No Cloud)

```bash
# 1. Install Python 3.11+
python --version   # check

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your values

# 5. Generate password hash
python generate_hash.py
# Paste hash into secrets.toml as auth.PASSWORD_HASH

# 6. Run the app
streamlit run app.py --server.port 8501 --server.address localhost

# 7. Run scheduler (separate terminal)
python scheduler_runner.py
```

Open: [http://localhost:8501](http://localhost:8501)

---

## Method 3: Private Remote Access (Local + ngrok)

```bash
# Install ngrok (free)
pip install pyngrok

# Run app locally, then expose via ngrok
streamlit run app.py --server.port 8501 --server.address localhost &
ngrok http 8501
```

Share the `https://xxx.ngrok.io` URL with yourself only.

---

## Updating Your Deployment

After making changes to the code:

```bash
git add .
git commit -m "Update: description of changes"
git push origin main
```

Streamlit Cloud auto-redeploys within ~30 seconds.

---

## Important Notes for Streamlit Cloud

| Feature | Streamlit Cloud Behaviour |
|---|---|
| Database (SQLite) | Stored in `/tmp` — resets on restart |
| Parquet cache | Stored in `/tmp` — resets on restart |
| Zerodha token | Must re-authenticate after each restart |
| Scheduler | NOT supported — run `scheduler_runner.py` locally |
| Secrets | Persisted via Streamlit Secrets UI |
| Memory | 1GB RAM on free tier |

> For persistent storage, consider upgrading to Streamlit Teams or switching to a VPS.

---

## File Structure

```
trading_terminal_v2/
├── app.py                    ← Main entry point
├── auth.py                   ← Login + OTP
├── generate_hash.py          ← Run once for password hash
├── requirements.txt
├── README.md
├── DEPLOYMENT_GUIDE.md
├── scheduler_runner.py       ← Run locally for background jobs
│
├── .streamlit/
│   ├── config.toml           ← Theme + server config
│   └── secrets.toml          ← Local secrets (gitignored)
│
├── config/
│   ├── __init__.py
│   └── settings.py           ← Reads from st.secrets
│
├── broker/
│   ├── zerodha.py            ← Kite Connect integration
│   └── paper_trade.py        ← Simulated trading engine
│
├── data/
│   ├── fetcher.py            ← yfinance + Alpha Vantage
│   └── cache.py              ← SQLite + Parquet cache
│
├── analysis/
│   ├── technical.py          ← 5 strategy signals
│   ├── backtester.py         ← Backtrader engine
│   └── predictor.py          ← 12-24 month trend model
│
├── alerts/
│   ├── signal_engine.py      ← Signal logic
│   └── emailer.py            ← Gmail SMTP alerts
│
├── news/
│   └── fetcher.py            ← NewsAPI + Google News
│
└── ui/
    ├── components.py         ← Reusable dark UI components
    ├── portfolio_page.py
    ├── signals_page.py
    ├── backtest_page.py
    ├── news_page.py
    ├── paper_trade_page.py
    ├── search_page.py
    ├── zerodha_page.py
    └── alerts_page.py
```
