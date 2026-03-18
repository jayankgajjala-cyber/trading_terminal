"""
app.py ─ Trading Terminal  |  Main entry point
Professional dark terminal UI with collapsible side-nav.
Compatible with Streamlit Cloud.
"""

import streamlit as st

# ── Page config — MUST be first ──────────────────────────────────────────────
st.set_page_config(
    page_title="Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font import ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── Reset & base ──────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #060A12 !important;
    color: #C8D6E5 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Hide default streamlit chrome ──────────────────────────────────────── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="collapsedControl"]  { display: none !important; }

/* ── Sidebar — hide entirely (we use custom nav) ────────────────────────── */
[data-testid="stSidebar"] { display: none !important; }

/* ── Main content area ───────────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"],
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Shell layout ────────────────────────────────────────────────────────── */
.tt-shell {
    display: flex;
    min-height: 100vh;
    background: #060A12;
}

/* ── Side navigation ─────────────────────────────────────────────────────── */
.tt-nav {
    position: fixed;
    top: 0; left: 0;
    height: 100vh;
    width: 220px;
    background: #0A0F1C;
    border-right: 1px solid #141D2E;
    display: flex;
    flex-direction: column;
    z-index: 1000;
    transition: width 0.25s cubic-bezier(0.4,0,0.2,1);
    overflow: hidden;
}
.tt-nav.collapsed { width: 56px; }

/* Logo row */
.tt-nav-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 18px 14px 14px;
    border-bottom: 1px solid #141D2E;
    min-height: 60px;
    overflow: hidden;
    white-space: nowrap;
}
.tt-nav-logo-icon {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #00D4FF, #0066FF);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
    flex-shrink: 0;
}
.tt-nav-logo-text {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    font-weight: 600;
    color: #E8EDF5;
    letter-spacing: 0.04em;
    transition: opacity 0.2s;
}
.tt-nav.collapsed .tt-nav-logo-text { opacity: 0; }

/* Toggle button */
.tt-nav-toggle {
    position: absolute;
    top: 18px; right: -12px;
    width: 24px; height: 24px;
    background: #0A0F1C;
    border: 1px solid #1E2B40;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    color: #4A6080;
    font-size: 11px;
    transition: all 0.2s;
    z-index: 1001;
}
.tt-nav-toggle:hover { color: #00D4FF; border-color: #00D4FF; }

/* Nav items */
.tt-nav-items {
    flex: 1;
    padding: 12px 0;
    overflow-y: auto;
    overflow-x: hidden;
}
.tt-nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    margin: 2px 8px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
    text-decoration: none;
    color: #5A7299;
    font-size: 13px;
    font-weight: 400;
    border: 1px solid transparent;
}
.tt-nav-item:hover {
    background: #101828;
    color: #A0BCDA;
    border-color: #1A2540;
}
.tt-nav-item.active {
    background: #0E1F35;
    color: #00D4FF;
    border-color: #1A3A55;
    font-weight: 500;
}
.tt-nav-item-icon {
    font-size: 16px;
    width: 20px;
    text-align: center;
    flex-shrink: 0;
}
.tt-nav-item-label {
    font-size: 13px;
    transition: opacity 0.2s;
}
.tt-nav.collapsed .tt-nav-item-label { opacity: 0; }
.tt-nav.collapsed .tt-nav-item { padding: 10px; margin: 2px 6px; justify-content: center; }
.tt-nav.collapsed .tt-nav-item-icon { width: auto; }

/* Section divider in nav */
.tt-nav-divider {
    height: 1px;
    background: #141D2E;
    margin: 8px 14px;
}
.tt-nav-section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px;
    font-weight: 500;
    color: #2A3D58;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 6px 22px 2px;
    white-space: nowrap;
    transition: opacity 0.2s;
}
.tt-nav.collapsed .tt-nav-section-label { opacity: 0; }

/* Nav footer */
.tt-nav-footer {
    padding: 12px 8px;
    border-top: 1px solid #141D2E;
    overflow: hidden;
    white-space: nowrap;
}
.tt-nav-user {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 6px;
    border-radius: 8px;
}
.tt-nav-avatar {
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #0066FF22, #00D4FF22);
    border: 1px solid #00D4FF44;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #00D4FF;
    flex-shrink: 0;
}
.tt-nav-user-info { transition: opacity 0.2s; }
.tt-nav-user-name {
    font-size: 12px;
    font-weight: 500;
    color: #A0BCDA;
    line-height: 1.2;
}
.tt-nav-user-role {
    font-size: 10px;
    color: #2E4060;
    font-family: 'IBM Plex Mono', monospace;
}
.tt-nav.collapsed .tt-nav-user-info { opacity: 0; }

/* ── Page content ────────────────────────────────────────────────────────── */
.tt-content {
    margin-left: 220px;
    min-height: 100vh;
    padding: 28px 32px;
    transition: margin-left 0.25s cubic-bezier(0.4,0,0.2,1);
    background: #060A12;
}
.tt-content.nav-collapsed { margin-left: 56px; }

/* ── Top bar ─────────────────────────────────────────────────────────────── */
.tt-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
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
    margin-top: 2px;
    font-family: 'IBM Plex Mono', monospace;
}
.tt-market-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
}
.tt-market-badge.open {
    background: #0A2218;
    color: #00C87A;
    border: 1px solid #00C87A33;
}
.tt-market-badge.closed {
    background: #1A0D0D;
    color: #FF4444;
    border: 1px solid #FF444433;
}
.tt-market-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    animation: pulse-dot 2s infinite;
}
.open .tt-market-dot { background: #00C87A; }
.closed .tt-market-dot { background: #FF4444; animation: none; }
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ── Metric cards ────────────────────────────────────────────────────────── */
.tt-metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 24px;
}
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
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #00D4FF33, transparent);
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
.tt-metric-delta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    margin-top: 6px;
}
.tt-metric-delta.pos { color: #00C87A; }
.tt-metric-delta.neg { color: #FF4455; }
.tt-metric-delta.neu { color: #4A6080; }

/* ── Data table ──────────────────────────────────────────────────────────── */
.tt-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.tt-table thead tr {
    background: #080D18;
    border-bottom: 1px solid #141D2E;
}
.tt-table thead th {
    padding: 10px 14px;
    text-align: left;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    color: #2E4060;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.tt-table tbody tr {
    border-bottom: 1px solid #0D1525;
    transition: background 0.1s;
}
.tt-table tbody tr:hover { background: #0A1020; }
.tt-table tbody td {
    padding: 10px 14px;
    color: #8AA0BE;
    font-size: 13px;
}
.tt-table tbody td:first-child {
    color: #C8D6E5;
    font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
}

/* ── Signal badges ───────────────────────────────────────────────────────── */
.sig-buy  { background:#00281A; color:#00C87A; border:1px solid #00C87A44;
            padding:3px 10px; border-radius:4px; font-family:'IBM Plex Mono',monospace;
            font-size:11px; font-weight:600; letter-spacing:0.05em; }
.sig-sell { background:#280A0A; color:#FF4455; border:1px solid #FF445544;
            padding:3px 10px; border-radius:4px; font-family:'IBM Plex Mono',monospace;
            font-size:11px; font-weight:600; letter-spacing:0.05em; }
.sig-hold { background:#1A1400; color:#FFAA00; border:1px solid #FFAA0044;
            padding:3px 10px; border-radius:4px; font-family:'IBM Plex Mono',monospace;
            font-size:11px; font-weight:600; letter-spacing:0.05em; }

/* ── Panel / card ────────────────────────────────────────────────────────── */
.tt-panel {
    background: #0A0F1C;
    border: 1px solid #141D2E;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 18px;
}
.tt-panel-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
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
    content: '';
    width: 3px; height: 12px;
    background: #00D4FF;
    border-radius: 2px;
}

/* ── Section tabs (within page) ──────────────────────────────────────────── */
.tt-tabs { display: flex; gap: 4px; margin-bottom: 20px; }
.tt-tab {
    padding: 7px 16px;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: #3A5070;
    cursor: pointer;
    border: 1px solid transparent;
    background: transparent;
    transition: all 0.15s;
    white-space: nowrap;
}
.tt-tab:hover { color: #6A90B0; background: #0A1020; }
.tt-tab.active {
    color: #00D4FF;
    background: #0A1828;
    border-color: #1A3A55;
}

/* ── Form elements ───────────────────────────────────────────────────────── */
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
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #00D4FF66 !important;
    box-shadow: 0 0 0 2px #00D4FF11 !important;
}
label, .stTextInput label, .stSelectbox label,
.stNumberInput label, .stTextArea label {
    color: #3A5070 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button {
    background: #0A1828 !important;
    color: #00D4FF !important;
    border: 1px solid #1A3A55 !important;
    border-radius: 7px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    transition: all 0.15s !important;
    letter-spacing: 0.03em !important;
}
.stButton > button:hover {
    background: #0E2238 !important;
    border-color: #00D4FF66 !important;
    box-shadow: 0 0 16px #00D4FF18 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #003D66, #005588) !important;
    border-color: #00D4FF55 !important;
    box-shadow: 0 0 20px #00D4FF15 !important;
}

/* ── Charts ──────────────────────────────────────────────────────────────── */
.js-plotly-plot, .plotly { background: transparent !important; }

/* ── Divider ─────────────────────────────────────────────────────────────── */
hr { border-color: #141D2E !important; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #060A12; }
::-webkit-scrollbar-thumb { background: #1A2540; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #2A3A58; }

/* ── Streamlit dataframe override ────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #141D2E !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
.stDataFrame iframe { background: transparent !important; }

/* ── Alert / info boxes ───────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background: #0A1020 !important;
    border: 1px solid #1A2540 !important;
    border-radius: 8px !important;
    color: #8AA0BE !important;
}

/* ── Spinner ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: #00D4FF !important; }

/* ── Metric widget ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #0A0F1C;
    border: 1px solid #141D2E;
    border-radius: 10px;
    padding: 14px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #E8EDF5 !important;
    font-size: 20px !important;
}
[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    color: #2E4060 !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}
[data-testid="stMetricDelta"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
}

/* ── Radio buttons (hidden — we use custom nav) ──────────────────────────── */
.stRadio { display: none; }

/* ── Tabs (native streamlit) ─────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: #080D18;
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
    border: 1px solid #141D2E;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important;
    color: #3A5070 !important;
    border-radius: 6px !important;
    padding: 6px 14px !important;
    border: none !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #0A1828 !important;
    color: #00D4FF !important;
}
[data-testid="stTabs"] [role="tabpanel"] {
    padding-top: 16px !important;
}

/* ── Grid helpers ────────────────────────────────────────────────────────── */
.tt-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.tt-grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

/* ── Confidence bar ──────────────────────────────────────────────────────── */
.conf-bar-bg {
    background: #141D2E;
    border-radius: 3px;
    height: 5px;
    width: 80px;
    display: inline-block;
    vertical-align: middle;
    overflow: hidden;
}
.conf-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, #00D4FF, #0066FF);
}

/* ── Progress / loading skeleton ────────────────────────────────────────── */
@keyframes shimmer {
    0% { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}
.tt-skeleton {
    background: linear-gradient(90deg, #0A0F1C 25%, #101828 50%, #0A0F1C 75%);
    background-size: 400px 100%;
    animation: shimmer 1.4s infinite;
    border-radius: 6px;
    height: 16px;
    margin: 8px 0;
}

/* ── News card ───────────────────────────────────────────────────────────── */
.tt-news-card {
    background: #0A0F1C;
    border: 1px solid #141D2E;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    transition: border-color 0.15s;
}
.tt-news-card:hover { border-color: #1A2D48; }
.tt-news-title {
    color: #A8C0D8;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.45;
    margin-bottom: 6px;
    text-decoration: none;
    display: block;
}
.tt-news-title:hover { color: #00D4FF; }
.tt-news-meta {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #2A3D58;
}

/* ── Connection status pill ──────────────────────────────────────────────── */
.tt-conn-pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 500;
}
.tt-conn-pill.connected {
    background: #0A2218;
    color: #00C87A;
    border: 1px solid #00C87A33;
}
.tt-conn-pill.disconnected {
    background: #1A1000;
    color: #FFAA00;
    border: 1px solid #FFAA0033;
}

/* ── Logout button ───────────────────────────────────────────────────────── */
.tt-logout-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    color: #2A3D58;
    cursor: pointer;
    transition: all 0.15s;
    width: 100%;
    white-space: nowrap;
}
.tt-logout-btn:hover { color: #FF4455; background: #1A0A0A; }
</style>
""", unsafe_allow_html=True)

# ── Auth check ────────────────────────────────────────────────────────────────
from auth import is_authenticated, render_login_page

if not is_authenticated():
    render_login_page()
    st.stop()

# ── Session state defaults ────────────────────────────────────────────────────
if "nav_collapsed" not in st.session_state:
    st.session_state.nav_collapsed = False
if "active_page" not in st.session_state:
    st.session_state.active_page = "portfolio"

# ── Navigation data ───────────────────────────────────────────────────────────
NAV_ITEMS = [
    {"id": "portfolio",  "icon": "◈",  "label": "Portfolio"},
    {"id": "signals",    "icon": "⬡",  "label": "Signals"},
    {"id": "backtest",   "icon": "◐",  "label": "Backtesting"},
    {"id": "news",       "icon": "◎",  "label": "News Feed"},
    {"id": "paper",      "icon": "◇",  "label": "Paper Trade"},
    {"id": "search",     "icon": "◉",  "label": "Stock Search"},
]

SYSTEM_ITEMS = [
    {"id": "zerodha",    "icon": "⬡",  "label": "Zerodha"},
    {"id": "alerts",     "icon": "◈",  "label": "Alerts"},
]

collapsed = st.session_state.nav_collapsed
nav_class = "tt-nav collapsed" if collapsed else "tt-nav"
content_class = "tt-content nav-collapsed" if collapsed else "tt-content"
toggle_icon = "›" if collapsed else "‹"

# ── Build nav HTML ─────────────────────────────────────────────────────────────
def nav_item_html(item, active_id):
    is_active = item["id"] == active_id
    cls = "tt-nav-item active" if is_active else "tt-nav-item"
    return f"""
    <div class="{cls}" onclick="setPage('{item['id']}')">
        <span class="tt-nav-item-icon">{item['icon']}</span>
        <span class="tt-nav-item-label">{item['label']}</span>
    </div>"""

active_page = st.session_state.active_page
nav_items_html = "".join([nav_item_html(i, active_page) for i in NAV_ITEMS])
sys_items_html = "".join([nav_item_html(i, active_page) for i in SYSTEM_ITEMS])

st.markdown(f"""
<div class="{nav_class}" id="tt-nav">
  <div class="tt-nav-logo">
    <div class="tt-nav-logo-icon">📈</div>
    <span class="tt-nav-logo-text">TRADE TERMINAL</span>
  </div>
  <div class="tt-nav-toggle" onclick="toggleNav()" title="Toggle sidebar">
    <span id="toggle-icon">{toggle_icon}</span>
  </div>

  <div class="tt-nav-items">
    <div class="tt-nav-section-label">Analytics</div>
    {nav_items_html}
    <div class="tt-nav-divider"></div>
    <div class="tt-nav-section-label">System</div>
    {sys_items_html}
  </div>

  <div class="tt-nav-footer">
    <div class="tt-nav-user">
      <div class="tt-nav-avatar">JK</div>
      <div class="tt-nav-user-info">
        <div class="tt-nav-user-name">Jayank</div>
        <div class="tt-nav-user-role">PRIVATE ACCOUNT</div>
      </div>
    </div>
  </div>
</div>

<script>
function setPage(pageId) {{
    // Use Streamlit's component value mechanism via hidden input trick
    const input = window.parent.document.querySelector('input[aria-label="__nav_page__"]');
    if (input) {{
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(input, pageId);
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
}}
function toggleNav() {{
    const input = window.parent.document.querySelector('input[aria-label="__nav_toggle__"]');
    if (input) {{
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(input, 'toggle_' + Date.now());
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
    }}
}}
</script>
""", unsafe_allow_html=True)

# ── Hidden nav controls ───────────────────────────────────────────────────────
# These hidden inputs receive the JS clicks and trigger reruns
with st.sidebar:
    nav_page_val = st.text_input("", key="nav_page_input",
                                  label_visibility="collapsed")
    nav_toggle_val = st.text_input("", key="nav_toggle_input",
                                    label_visibility="collapsed")

# Process nav changes
_nav_in = st.session_state.get("nav_page_input", "")
if _nav_in and _nav_in != st.session_state.active_page:
    valid_ids = [i["id"] for i in NAV_ITEMS + SYSTEM_ITEMS]
    if _nav_in in valid_ids:
        st.session_state.active_page = _nav_in
        st.rerun()

_tog_in = st.session_state.get("nav_toggle_input", "")
if _tog_in and _tog_in.startswith("toggle_"):
    st.session_state.nav_collapsed = not st.session_state.nav_collapsed
    st.session_state.nav_toggle_input = ""
    st.rerun()

# ── Sidebar radio fallback (works reliably with Streamlit) ────────────────────
# This is a RELIABLE fallback navigation using native Streamlit sidebar radio
# The custom JS nav above enhances the visual; this radio drives actual routing
with st.sidebar:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: block !important; width: 0 !important;
        min-width: 0 !important; overflow: hidden !important; opacity: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    page_choice = st.radio(
        "page",
        options=[i["id"] for i in NAV_ITEMS + SYSTEM_ITEMS],
        index=[i["id"] for i in NAV_ITEMS + SYSTEM_ITEMS].index(active_page),
        key="sidebar_nav",
        label_visibility="collapsed"
    )
    if page_choice != active_page:
        st.session_state.active_page = page_choice
        st.rerun()

# ── Content wrapper ───────────────────────────────────────────────────────────
st.markdown(f'<div class="{content_class}">', unsafe_allow_html=True)

# ── Market hours status ────────────────────────────────────────────────────────
from datetime import datetime
import pytz
IST = pytz.timezone("Asia/Kolkata")
now_ist = datetime.now(IST)
is_market = (now_ist.weekday() < 5 and
             9 * 60 + 15 <= now_ist.hour * 60 + now_ist.minute <= 15 * 60 + 30)

market_html = f"""
<span class="tt-market-badge {'open' if is_market else 'closed'}">
  <span class="tt-market-dot"></span>
  {'NSE OPEN' if is_market else 'NSE CLOSED'}
  &nbsp;·&nbsp; {now_ist.strftime('%H:%M IST')}
</span>"""

# ── Page titles ───────────────────────────────────────────────────────────────
PAGE_META = {
    "portfolio": ("Portfolio Overview",   "Holdings, P&L, allocation & budget"),
    "signals":   ("Strategy Signals",     "Live technical analysis signals"),
    "backtest":  ("Backtesting",          "Historical strategy performance"),
    "news":      ("News Feed",            "Market news & sentiment"),
    "paper":     ("Paper Trading",        "Simulated trades & portfolio"),
    "search":    ("Stock Search",         "Full analysis for any NSE stock"),
    "zerodha":   ("Zerodha Connect",      "Broker account & API settings"),
    "alerts":    ("Alert Settings",       "Email notifications & scheduler"),
}
title, subtitle = PAGE_META.get(active_page, ("Terminal", ""))

st.markdown(f"""
<div class="tt-topbar">
  <div>
    <div class="tt-page-title">{title}</div>
    <div class="tt-page-subtitle">{subtitle}</div>
  </div>
  {market_html}
</div>
""", unsafe_allow_html=True)

# ── Route to pages ─────────────────────────────────────────────────────────────
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

st.markdown('</div>', unsafe_allow_html=True)
