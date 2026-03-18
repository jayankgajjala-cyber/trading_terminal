"""
app.py — Trading Terminal  |  Streamlit Cloud compatible.
Navigation uses the native Streamlit sidebar (fully reliable).
Custom CSS makes it look like a professional dark terminal.
"""
import streamlit as st

st.set_page_config(
    page_title="Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth check ────────────────────────────────────────────────────────────────
from auth import is_authenticated, render_login_page
if not is_authenticated():
    render_login_page()
    st.stop()

# ── Session defaults ──────────────────────────────────────────────────────────
if "active_page" not in st.session_state:
    st.session_state.active_page = "portfolio"

# ── Global dark theme CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #060A12 !important;
    color: #C8D6E5 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

/* ── Sidebar shell ── */
[data-testid="stSidebar"] {
    background: #0A0F1C !important;
    border-right: 1px solid #141D2E !important;
    min-width: 220px !important;
    max-width: 220px !important;
}
[data-testid="stSidebar"] > div:first-child {
    background: #0A0F1C !important;
    padding: 0 !important;
}

/* Collapse toggle button */
[data-testid="collapsedControl"] {
    background: #0A0F1C !important;
    border-right: 1px solid #141D2E !important;
    color: #2A3D58 !important;
}
[data-testid="collapsedControl"]:hover { color: #00D4FF !important; }

/* ── Sidebar content typography ── */
[data-testid="stSidebar"] * {
    font-family: 'IBM Plex Mono', monospace !important;
}

/* ── Hide radio button circles ── */
[data-testid="stSidebar"] [data-testid="stRadio"] label div:first-child {
    display: none !important;
}

/* ── Radio option styling → nav items ── */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    padding: 9px 14px !important;
    margin: 2px 8px !important;
    border-radius: 8px !important;
    border: 1px solid transparent !important;
    color: #5A7299 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    white-space: nowrap !important;
    gap: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: #101828 !important;
    color: #A0BCDA !important;
    border-color: #1A2540 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-checked="true"] {
    background: #0E1F35 !important;
    color: #00D4FF !important;
    border-color: #1A3A55 !important;
    font-weight: 500 !important;
}
/* Checked state via parent div */
[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
    background: #0E1F35 !important;
    color: #00D4FF !important;
    border-color: #1A3A55 !important;
    font-weight: 500 !important;
}

/* Hide radio group label */
[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    display: none !important;
}

/* ── Sidebar divider ── */
[data-testid="stSidebar"] hr {
    border-color: #141D2E !important;
    margin: 8px 14px !important;
}

/* ── Sidebar section label ── */
.nav-section {
    font-size: 9px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    color: #1E3050 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    padding: 10px 22px 4px !important;
}

/* ── Main content ── */
[data-testid="stMainBlockContainer"],
.main .block-container {
    padding: 28px 32px !important;
    max-width: 100% !important;
    background: #060A12 !important;
}

/* ── Top bar ── */
.tt-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
    padding-bottom: 18px;
    border-bottom: 1px solid #0D1525;
}
.tt-page-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 20px;
    font-weight: 600;
    color: #E8EDF5;
    letter-spacing: -0.01em;
}
.tt-page-subtitle {
    font-size: 12px;
    color: #2E4060;
    margin-top: 3px;
    font-family: 'IBM Plex Mono', monospace;
}
.tt-market-badge {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 6px 14px;
    border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
}
.tt-market-badge.open  { background:#0A2218; color:#00C87A; border:1px solid #00C87A33; }
.tt-market-badge.closed{ background:#1A0D0D; color:#FF4444; border:1px solid #FF444433; }
.tt-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    display: inline-block;
}
.open  .tt-dot { background: #00C87A; animation: pulse 2s infinite; }
.closed .tt-dot { background: #FF4444; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── Metric cards ── */
.tt-metric {
    background: #0A0F1C;
    border: 1px solid #141D2E;
    border-radius: 10px;
    padding: 16px 18px;
    position: relative;
    overflow: hidden;
}
.tt-metric::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #00D4FF22, transparent);
}
.tt-metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    color: #2E4060;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
}
.tt-metric-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #E8EDF5;
    line-height: 1;
}
.tt-metric-delta { font-family:'IBM Plex Mono',monospace; font-size:11px; margin-top:6px; }
.tt-metric-delta.pos { color: #00C87A; }
.tt-metric-delta.neg { color: #FF4455; }
.tt-metric-delta.neu { color: #4A6080; }

/* ── Panel ── */
.tt-panel {
    background: #0A0F1C;
    border: 1px solid #141D2E;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 18px;
}
.tt-panel-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: #3A5070;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.tt-panel-title::before {
    content:''; width:3px; height:12px;
    background:#00D4FF; border-radius:2px;
}

/* ── Table ── */
.tt-table { width:100%; border-collapse:collapse; font-size:13px; }
.tt-table thead tr { background:#080D18; border-bottom:1px solid #141D2E; }
.tt-table thead th {
    padding:10px 14px; text-align:left;
    font-family:'IBM Plex Mono',monospace; font-size:10px;
    font-weight:500; color:#2E4060;
    text-transform:uppercase; letter-spacing:0.08em;
}
.tt-table tbody tr { border-bottom:1px solid #0D1525; transition:background 0.1s; }
.tt-table tbody tr:hover { background:#0A1020; }
.tt-table tbody td { padding:10px 14px; color:#8AA0BE; font-size:13px; }
.tt-table tbody td:first-child {
    color:#C8D6E5; font-weight:500;
    font-family:'IBM Plex Mono',monospace;
}

/* ── Signal badges ── */
.sig-buy  { background:#00281A; color:#00C87A; border:1px solid #00C87A44;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }
.sig-sell { background:#280A0A; color:#FF4455; border:1px solid #FF445544;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }
.sig-hold { background:#1A1400; color:#FFAA00; border:1px solid #FFAA0044;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }

/* ── Confidence bar ── */
.conf-bar-bg {
    background:#141D2E; border-radius:3px; height:5px;
    width:80px; display:inline-block; vertical-align:middle; overflow:hidden;
}
.conf-bar-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#00D4FF,#0066FF); }

/* ── Section header ── */
.tt-section {
    display:flex; align-items:center; gap:10px;
    margin:24px 0 14px;
}
.tt-section-bar { width:3px; height:14px; background:#00D4FF; border-radius:2px; }
.tt-section-label {
    font-family:'IBM Plex Mono',monospace; font-size:11px;
    font-weight:500; color:#3A5070;
    text-transform:uppercase; letter-spacing:0.1em;
}

/* ── Empty state ── */
.tt-empty {
    text-align:center; padding:48px 24px;
    background:#0A0F1C; border:1px dashed #141D2E; border-radius:12px;
}
.tt-empty-icon { font-size:28px; margin-bottom:12px; opacity:0.3; }
.tt-empty-msg  { font-family:'IBM Plex Mono',monospace; font-size:13px; color:#2A3D58; }
.tt-empty-hint { color:#1A2D40; font-size:12px; margin-top:8px; }

/* ── News card ── */
.tt-news-card {
    background:#0A0F1C; border:1px solid #141D2E;
    border-radius:10px; padding:14px 18px; margin-bottom:10px;
    transition:border-color 0.15s;
}
.tt-news-card:hover { border-color:#1A2D48; }
.tt-news-title {
    color:#A8C0D8; font-size:14px; font-weight:500;
    line-height:1.45; margin-bottom:6px;
    text-decoration:none; display:block;
}
.tt-news-title:hover { color:#00D4FF; }
.tt-news-meta { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#2A3D58; }

/* ── Form elements ── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #080D18 !important;
    border: 1px solid #1A2540 !important;
    border-radius: 7px !important;
    color: #C8D6E5 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 13px !important;
}
label, .stTextInput label, .stSelectbox label,
.stNumberInput label, .stTextArea label {
    color: #3A5070 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #0A1828 !important;
    color: #00D4FF !important;
    border: 1px solid #1A3A55 !important;
    border-radius: 7px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    letter-spacing: 0.03em !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    background: #0E2238 !important;
    border-color: #00D4FF66 !important;
    box-shadow: 0 0 16px #00D4FF18 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #003D66, #005588) !important;
    border-color: #00D4FF55 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: #080D18; border-radius: 8px;
    padding: 4px; gap: 2px; border: 1px solid #141D2E;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; color: #3A5070 !important;
    border-radius: 6px !important; padding: 6px 14px !important;
    border: none !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #0A1828 !important; color: #00D4FF !important;
}
[data-testid="stTabs"] [role="tabpanel"] { padding-top: 16px !important; }

/* ── Streamlit native metric ── */
[data-testid="stMetric"] {
    background: #0A0F1C; border: 1px solid #141D2E;
    border-radius: 10px; padding: 14px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #E8EDF5 !important; font-size: 20px !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #2E4060 !important; font-size: 10px !important;
    text-transform: uppercase !important; letter-spacing: 0.1em !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #141D2E !important;
    border-radius: 10px !important; overflow: hidden !important;
}

/* ── Alert boxes ── */
[data-testid="stAlert"] {
    background: #0A1020 !important; border: 1px solid #1A2540 !important;
    border-radius: 8px !important; color: #8AA0BE !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #060A12; }
::-webkit-scrollbar-thumb { background: #1A2540; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #2A3A58; }

/* ── Charts transparent bg ── */
.js-plotly-plot, .plotly { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("portfolio", "◈  Portfolio"),
    ("signals",   "⬡  Signals"),
    ("backtest",  "◐  Backtesting"),
    ("news",      "◎  News & AI Insights"),
    ("paper",     "◇  Paper Trade"),
    ("search",    "◉  Stock Search"),
]
SYSTEM_ITEMS = [
    ("zerodha",   "⬡  Zerodha"),
    ("alerts",    "◈  Alerts"),
]
ALL_ITEMS = NAV_ITEMS + SYSTEM_ITEMS

with st.sidebar:
    # ── Logo ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding:18px 16px 14px;border-bottom:1px solid #141D2E;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:28px;height:28px;background:linear-gradient(135deg,#00D4FF,#0066FF);
                    border-radius:6px;display:flex;align-items:center;justify-content:center;
                    font-size:14px;flex-shrink:0">📈</div>
        <div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600;
                      color:#E8EDF5;letter-spacing:0.06em">TRADE TERMINAL</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                      color:#1E3050;letter-spacing:0.1em">PRIVATE ACCOUNT</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Analytics section ─────────────────────────────────────────────────────
    st.markdown('<div class="nav-section">Analytics</div>', unsafe_allow_html=True)

    active = st.session_state.active_page
    for page_id, label in NAV_ITEMS:
        # Highlight active item with different styling via button
        if page_id == active:
            btn_style = ("background:#0E1F35;color:#00D4FF;border:1px solid #1A3A55;"
                         "border-radius:8px;padding:9px 14px;margin:2px 8px;width:calc(100% - 16px);"
                         "font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:500;"
                         "cursor:default;display:block;text-align:left;")
        else:
            btn_style = ("background:transparent;color:#5A7299;border:1px solid transparent;"
                         "border-radius:8px;padding:9px 14px;margin:2px 8px;width:calc(100% - 16px);"
                         "font-family:'IBM Plex Mono',monospace;font-size:13px;"
                         "cursor:pointer;display:block;text-align:left;")

        if st.button(label, key=f"nav_{page_id}",
                     use_container_width=True):
            st.session_state.active_page = page_id
            st.rerun()

    # ── System section ────────────────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown('<div class="nav-section">System</div>', unsafe_allow_html=True)

    for page_id, label in SYSTEM_ITEMS:
        if st.button(label, key=f"nav_{page_id}",
                     use_container_width=True):
            st.session_state.active_page = page_id
            st.rerun()

    # ── User footer ───────────────────────────────────────────────────────────
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown("""
    <div style="padding:8px 14px">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="width:28px;height:28px;background:#0A1828;border:1px solid #00D4FF33;
                    border-radius:6px;display:flex;align-items:center;justify-content:center;
                    font-family:'IBM Plex Mono',monospace;font-size:11px;color:#00D4FF">JK</div>
        <div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                      font-weight:500;color:#A0BCDA">Jayank</div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#1E3050">
            PRIVATE ACCOUNT</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("⎋  Logout", key="logout_btn", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ── Market hours status ───────────────────────────────────────────────────────
from datetime import datetime
import pytz
IST = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(IST)
is_market = (now_ist.weekday() < 5 and
             9 * 60 + 15 <= now_ist.hour * 60 + now_ist.minute <= 15 * 60 + 30)

# ── Page header ───────────────────────────────────────────────────────────────
PAGE_META = {
    "portfolio": ("Portfolio Overview",  "Holdings, P&L, allocation & budget"),
    "signals":   ("Strategy Signals",    "Live technical analysis signals"),
    "backtest":  ("Backtesting",         "Historical strategy performance"),
    "news":      ("News & AI Insights",   "AI analysis · sentiment · conflict detection"),
    "paper":     ("Paper Trading",       "Simulated trades & portfolio"),
    "search":    ("Stock Search",        "Full analysis for any NSE stock"),
    "zerodha":   ("Zerodha Connect",     "Broker account & API settings"),
    "alerts":    ("Alert Settings",      "Email notifications & scheduler"),
}
active_page = st.session_state.active_page
title, subtitle = PAGE_META.get(active_page, ("Terminal", ""))

st.markdown(f"""
<div class="tt-topbar">
  <div>
    <div class="tt-page-title">{title}</div>
    <div class="tt-page-subtitle">{subtitle}</div>
  </div>
  <span class="tt-market-badge {'open' if is_market else 'closed'}">
    <span class="tt-dot"></span>
    {'NSE OPEN' if is_market else 'NSE CLOSED'}
    &nbsp;·&nbsp; {now_ist.strftime('%H:%M IST')}
  </span>
</div>
""", unsafe_allow_html=True)

# ── Route to pages ────────────────────────────────────────────────────────────
if active_page == "portfolio":
    from ui.portfolio_page import render; render()
elif active_page == "signals":
    from ui.signals_page import render; render()
elif active_page == "backtest":
    from ui.backtest_page import render; render()
elif active_page == "news":
    from ui.news_page import render; render()
elif active_page == "paper":
    from ui.paper_trade_page import render; render()
elif active_page == "search":
    from ui.search_page import render; render()
elif active_page == "zerodha":
    from ui.zerodha_page import render; render()
elif active_page == "alerts":
    from ui.alerts_page import render; render()
