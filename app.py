"""
app.py — Trading Terminal
Custom collapsible sidebar: icons visible when collapsed, full labels when expanded.
No "Keyboard shortcut" label. Proper TRADE TERMINAL branding.
Works on Streamlit Cloud.
"""
import streamlit as st
from datetime import datetime
import pytz

st.set_page_config(
    page_title="Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth ──────────────────────────────────────────────────────────────────────
from auth import is_authenticated, render_login_page
if not is_authenticated():
    render_login_page()
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "active_page"    not in st.session_state: st.session_state.active_page    = "portfolio"
if "nav_expanded"   not in st.session_state: st.session_state.nav_expanded   = True

# ── Navigation definitions ────────────────────────────────────────────────────
NAV = [
    ("portfolio", "📊", "Portfolio"),
    ("signals",   "🎯", "Signals"),
    ("backtest",  "📈", "Backtesting"),
    ("news",      "📰", "News & AI"),
    ("paper",     "🧪", "Paper Trade"),
    ("search",    "🔍", "Stock Search"),
]
SYS = [
    ("zerodha",  "🔗", "Zerodha"),
    ("alerts",   "🔔", "Alerts"),
]

PAGE_META = {
    "portfolio": ("Portfolio Overview",   "Holdings · P&L · allocation · budget"),
    "signals":   ("Strategy Signals",     "Live technical analysis · deep research"),
    "backtest":  ("Backtesting",          "Historical strategy validation · ₹10,000 capital"),
    "news":      ("News & AI Insights",   "AI sentiment · conflict detection · recommendations"),
    "paper":     ("Paper Trading",        "Simulated trades · P&L tracking"),
    "search":    ("Stock Search",         "Full analysis for any NSE stock"),
    "zerodha":   ("Zerodha Connect",      "Broker account & API settings"),
    "alerts":    ("Alert Settings",       "Email alerts · Excel export · scheduler"),
}

expanded    = st.session_state.nav_expanded
active_page = st.session_state.active_page
nav_w       = 220 if expanded else 60
content_ml  = nav_w + 8

IST = pytz.timezone("Asia/Kolkata")
now_ist  = datetime.now(IST)
is_market = (now_ist.weekday() < 5 and
             9*60+15 <= now_ist.hour*60+now_ist.minute <= 15*60+30)

title, subtitle = PAGE_META.get(active_page, ("Terminal", ""))

# ── Hide ALL native Streamlit chrome including sidebar ─────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
[data-testid="stMainBlockContainer"],
.main { background: #060A12 !important; }

/* Hide ALL native chrome */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] { display: none !important; }

/* Main block — no padding, full width */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
    margin: 0 !important;
}

/* ── Custom nav shell ──────────────────────────────────────────────── */
.tt-nav {
    position: fixed;
    top: 0; left: 0;
    height: 100vh;
    background: #0A0F1C;
    border-right: 1px solid #141D2E;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width 0.22s cubic-bezier(0.4,0,0.2,1);
}
.tt-nav.expanded  { width: 220px; }
.tt-nav.collapsed { width: 60px;  }

/* Logo row */
.tt-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 14px 14px;
    border-bottom: 1px solid #141D2E;
    min-height: 58px;
    overflow: hidden;
    white-space: nowrap;
}
.tt-logo-icon {
    width: 30px; height: 30px; flex-shrink: 0;
    background: linear-gradient(135deg,#00D4FF,#0055CC);
    border-radius: 7px;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px;
}
.tt-logo-text {
    display: flex; flex-direction: column;
    transition: opacity 0.18s;
}
.tt-logo-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; font-weight: 600;
    color: #E8EDF5; letter-spacing: 0.07em;
    line-height: 1.2;
}
.tt-logo-sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; color: #1E3050; letter-spacing: 0.1em;
}
.tt-nav.collapsed .tt-logo-text { opacity: 0; pointer-events: none; }

/* Toggle button */
.tt-toggle {
    position: absolute;
    top: 16px; right: -11px;
    width: 22px; height: 22px;
    background: #0A0F1C;
    border: 1px solid #1E2D44;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    font-size: 10px; color: #3A5070;
    transition: all 0.15s;
    z-index: 10000;
}
.tt-toggle:hover { color: #00D4FF; border-color: #00D4FF; background: #081220; }

/* Section labels */
.tt-sec-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; color: #1A2D44;
    letter-spacing: 0.14em; text-transform: uppercase;
    padding: 10px 18px 4px;
    white-space: nowrap;
    transition: opacity 0.18s;
}
.tt-nav.collapsed .tt-sec-label { opacity: 0; }

/* Nav items */
.tt-nav-items { flex: 1; padding: 6px 0; overflow-y: auto; overflow-x: hidden; }
.tt-nav-items::-webkit-scrollbar { width: 0; }

.tt-item {
    display: flex; align-items: center; gap: 11px;
    padding: 9px 14px; margin: 2px 7px;
    border-radius: 8px; border: 1px solid transparent;
    cursor: pointer; white-space: nowrap;
    text-decoration: none;
    color: #4A6888; font-size: 13px; font-weight: 400;
    font-family: 'IBM Plex Mono', monospace;
    transition: all 0.13s;
    position: relative;
}
.tt-item:hover {
    background: #0D1828; color: #90B0D0;
    border-color: #1A2D44;
}
.tt-item.active {
    background: #0B1E36; color: #00D4FF;
    border-color: #153A5A; font-weight: 500;
}
.tt-item-icon {
    font-size: 16px; width: 22px; text-align: center; flex-shrink: 0;
}
.tt-item-label { transition: opacity 0.18s; }
.tt-nav.collapsed .tt-item-label { opacity: 0; pointer-events: none; }
.tt-nav.collapsed .tt-item { padding: 9px; margin: 2px 7px; justify-content: center; }
.tt-nav.collapsed .tt-item-icon { width: auto; }

/* Tooltip on collapsed */
.tt-item[data-tip]:hover::after {
    content: attr(data-tip);
    position: absolute; left: 52px; top: 50%;
    transform: translateY(-50%);
    background: #0D1828; color: #C8D6E5;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; padding: 5px 10px;
    border-radius: 6px; border: 1px solid #1A2D44;
    white-space: nowrap; z-index: 99999;
    pointer-events: none;
}

/* Divider */
.tt-divider { height:1px; background:#0E1928; margin:8px 12px; }

/* Footer */
.tt-footer {
    padding: 10px 8px; border-top: 1px solid #0E1928;
    overflow: hidden; white-space: nowrap;
}
.tt-user {
    display: flex; align-items: center; gap: 9px;
    padding: 7px 6px; border-radius: 7px;
}
.tt-avatar {
    width: 28px; height: 28px; flex-shrink: 0;
    background: #0B1E36; border: 1px solid #00D4FF2A;
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; color: #00D4FF;
}
.tt-user-info { transition: opacity 0.18s; }
.tt-user-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px; font-weight: 500; color: #90B0D0; line-height: 1.2;
}
.tt-user-role {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; color: #1A2D44;
}
.tt-nav.collapsed .tt-user-info { opacity: 0; pointer-events: none; }

/* ── Content area ─────────────────────────────────────────────────── */
.tt-content {
    background: #060A12;
    min-height: 100vh;
    padding: 24px 28px 40px;
    transition: margin-left 0.22s cubic-bezier(0.4,0,0.2,1);
}

/* ── Top bar ─────────────────────────────────────────────────────── */
.tt-topbar {
    display: flex; align-items: center;
    justify-content: space-between;
    margin-bottom: 26px; padding-bottom: 16px;
    border-bottom: 1px solid #0D1525;
}
.tt-page-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 19px; font-weight: 600;
    color: #E8EDF5; letter-spacing: -0.01em;
}
.tt-page-subtitle {
    font-size: 12px; color: #2A3D58; margin-top: 3px;
    font-family: 'IBM Plex Mono', monospace;
}
.tt-badge {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 5px 13px; border-radius: 20px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; font-weight: 500;
}
.tt-badge.open   { background:#0A2218; color:#00C87A; border:1px solid #00C87A33; }
.tt-badge.closed { background:#1A0D0D; color:#FF4444; border:1px solid #FF444433; }
.tt-dot { width:6px; height:6px; border-radius:50%; display:inline-block; }
.open   .tt-dot { background:#00C87A; animation:pulse 2s infinite; }
.closed .tt-dot { background:#FF4444; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── Streamlit widgets dark styling ────────────────────────────── */
[data-testid="stMetric"] {
    background:#0A0F1C; border:1px solid #141D2E;
    border-radius:10px; padding:14px 16px !important;
}
[data-testid="stMetricValue"] {
    font-family:'IBM Plex Mono',monospace !important;
    color:#E8EDF5 !important; font-size:20px !important;
}
[data-testid="stMetricLabel"] {
    font-family:'IBM Plex Mono',monospace !important;
    color:#2E4060 !important; font-size:10px !important;
    text-transform:uppercase !important; letter-spacing:0.1em !important;
}
[data-testid="stDataFrame"] {
    border:1px solid #141D2E !important;
    border-radius:10px !important; overflow:hidden !important;
}
[data-testid="stAlert"] {
    background:#0A1020 !important; border:1px solid #1A2540 !important;
    border-radius:8px !important; color:#8AA0BE !important;
}
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background:#080D18 !important; border:1px solid #1A2540 !important;
    border-radius:7px !important; color:#C8D6E5 !important;
    font-family:'IBM Plex Mono',monospace !important; font-size:13px !important;
}
label, .stTextInput label, .stSelectbox label,
.stNumberInput label, .stTextArea label {
    color:#3A5070 !important; font-family:'IBM Plex Mono',monospace !important;
    font-size:11px !important; text-transform:uppercase !important;
    letter-spacing:0.08em !important;
}
.stButton > button {
    background:#0A1828 !important; color:#00D4FF !important;
    border:1px solid #1A3A55 !important; border-radius:7px !important;
    font-family:'IBM Plex Mono',monospace !important;
    font-size:12px !important; font-weight:500 !important;
    padding:8px 18px !important; letter-spacing:0.03em !important;
    transition:all 0.15s !important;
}
.stButton > button:hover {
    background:#0E2238 !important; border-color:#00D4FF66 !important;
}
.stButton > button[kind="primary"] {
    background:linear-gradient(135deg,#003D66,#005588) !important;
    border-color:#00D4FF55 !important;
}
[data-testid="stTabs"] [role="tablist"] {
    background:#080D18; border-radius:8px;
    padding:4px; gap:2px; border:1px solid #141D2E;
}
[data-testid="stTabs"] [role="tab"] {
    font-family:'IBM Plex Mono',monospace !important;
    font-size:11px !important; color:#3A5070 !important;
    border-radius:6px !important; padding:6px 14px !important;
    border:none !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background:#0A1828 !important; color:#00D4FF !important;
}
[data-testid="stTabs"] [role="tabpanel"] { padding-top:16px !important; }
hr { border-color:#141D2E !important; }
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:#060A12; }
::-webkit-scrollbar-thumb { background:#1A2540; border-radius:2px; }
.js-plotly-plot,.plotly { background:transparent !important; }

/* ── Reusable component classes ─────────────────────────────────── */
.tt-metric {
    background:#0A0F1C; border:1px solid #141D2E;
    border-radius:10px; padding:16px 18px; position:relative; overflow:hidden;
}
.tt-metric::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background:linear-gradient(90deg,#00D4FF22,transparent);
}
.tt-metric-label {
    font-family:'IBM Plex Mono',monospace; font-size:10px;
    color:#2E4060; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:8px;
}
.tt-metric-value {
    font-family:'IBM Plex Mono',monospace; font-size:22px;
    font-weight:600; color:#E8EDF5; line-height:1;
}
.tt-metric-delta { font-family:'IBM Plex Mono',monospace; font-size:11px; margin-top:6px; }
.tt-metric-delta.pos { color:#00C87A; }
.tt-metric-delta.neg { color:#FF4455; }
.tt-metric-delta.neu { color:#4A6080; }
.tt-panel {
    background:#0A0F1C; border:1px solid #141D2E;
    border-radius:12px; padding:20px 22px; margin-bottom:18px;
}
.tt-panel-title {
    font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:500;
    color:#3A5070; text-transform:uppercase; letter-spacing:0.1em;
    margin-bottom:16px; display:flex; align-items:center; gap:8px;
}
.tt-panel-title::before {
    content:''; width:3px; height:12px; background:#00D4FF; border-radius:2px;
}
.tt-table { width:100%; border-collapse:collapse; font-size:13px; }
.tt-table thead tr { background:#080D18; border-bottom:1px solid #141D2E; }
.tt-table thead th {
    padding:10px 14px; text-align:left;
    font-family:'IBM Plex Mono',monospace; font-size:10px;
    font-weight:500; color:#2E4060; text-transform:uppercase; letter-spacing:0.08em;
}
.tt-table tbody tr { border-bottom:1px solid #0D1525; transition:background 0.1s; }
.tt-table tbody tr:hover { background:#0A1020; }
.tt-table tbody td { padding:10px 14px; color:#8AA0BE; font-size:13px; }
.tt-table tbody td:first-child {
    color:#C8D6E5; font-weight:500; font-family:'IBM Plex Mono',monospace;
}
.sig-buy  { background:#00281A; color:#00C87A; border:1px solid #00C87A44;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }
.sig-sell { background:#280A0A; color:#FF4455; border:1px solid #FF445544;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }
.sig-hold { background:#1A1400; color:#FFAA00; border:1px solid #FFAA0044;
            padding:3px 10px; border-radius:4px;
            font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:600; }
.conf-bar-bg {
    background:#141D2E; border-radius:3px; height:5px; width:80px;
    display:inline-block; vertical-align:middle; overflow:hidden;
}
.conf-bar-fill { height:100%; border-radius:3px; background:linear-gradient(90deg,#00D4FF,#0066FF); }
.tt-section { display:flex; align-items:center; gap:10px; margin:24px 0 14px; }
.tt-section-bar { width:3px; height:14px; background:#00D4FF; border-radius:2px; }
.tt-section-label {
    font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:500;
    color:#3A5070; text-transform:uppercase; letter-spacing:0.1em;
}
.tt-empty {
    text-align:center; padding:48px 24px;
    background:#0A0F1C; border:1px dashed #141D2E; border-radius:12px;
}
.tt-empty-icon { font-size:28px; margin-bottom:12px; opacity:0.3; }
.tt-empty-msg  { font-family:'IBM Plex Mono',monospace; font-size:13px; color:#2A3D58; }
.tt-empty-hint { color:#1A2D40; font-size:12px; margin-top:8px; }
.tt-news-card {
    background:#0A0F1C; border:1px solid #141D2E;
    border-radius:10px; padding:14px 18px; margin-bottom:10px;
    transition:border-color 0.15s;
}
.tt-news-card:hover { border-color:#1A2D48; }
.tt-news-title {
    color:#A8C0D8; font-size:14px; font-weight:500;
    line-height:1.45; margin-bottom:6px; text-decoration:none; display:block;
}
.tt-news-title:hover { color:#00D4FF; }
.tt-news-meta { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#2A3D58; }
.nav-section {
    font-size:9px !important; font-family:'IBM Plex Mono',monospace !important;
    color:#1E3050 !important; letter-spacing:0.14em !important;
    text-transform:uppercase !important; padding:10px 22px 4px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Build custom nav HTML ─────────────────────────────────────────────────────
nav_class     = "tt-nav expanded" if expanded else "tt-nav collapsed"
toggle_symbol = "‹" if expanded else "›"

def _nav_item(page_id, icon, label, is_active, is_expanded):
    cls       = "tt-item active" if is_active else "tt-item"
    tip_attr  = "" if is_expanded else f'data-tip="{label}"'
    lbl_span  = f'<span class="tt-item-label">{label}</span>' if is_expanded else \
                f'<span class="tt-item-label">{label}</span>'
    return f"""
    <div class="{cls}" {tip_attr} onclick="navClick('{page_id}')">
      <span class="tt-item-icon">{icon}</span>
      {lbl_span}
    </div>"""

nav_items_html = "".join(_nav_item(p,i,l, p==active_page, expanded) for p,i,l in NAV)
sys_items_html = "".join(_nav_item(p,i,l, p==active_page, expanded) for p,i,l in SYS)

st.markdown(f"""
<div class="{nav_class}" id="tt-nav-root">

  <div class="tt-logo">
    <div class="tt-logo-icon">📈</div>
    <div class="tt-logo-text">
      <span class="tt-logo-name">TRADE TERMINAL</span>
      <span class="tt-logo-sub">PRIVATE ACCOUNT</span>
    </div>
  </div>

  <div class="tt-toggle" onclick="toggleNav()" title="{'Collapse sidebar' if expanded else 'Expand sidebar'}">
    {toggle_symbol}
  </div>

  <div class="tt-nav-items">
    <div class="tt-sec-label">Analytics</div>
    {nav_items_html}
    <div class="tt-divider"></div>
    <div class="tt-sec-label">System</div>
    {sys_items_html}
  </div>

  <div class="tt-footer">
    <div class="tt-user">
      <div class="tt-avatar">JK</div>
      <div class="tt-user-info">
        <div class="tt-user-name">Jayank</div>
        <div class="tt-user-role">PRIVATE ACCOUNT</div>
      </div>
    </div>
  </div>
</div>

<script>
// Nav click — write into hidden Streamlit text input, then fire React synthetic event
function navClick(pageId) {{
  var el = window.parent.document.querySelector('[data-testid="stTextInput"] input[aria-label="__nav__"]');
  if (!el) el = window.parent.document.querySelector('input[aria-label="__nav__"]');
  if (el) {{
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    setter.call(el, pageId);
    el.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}
}}
function toggleNav() {{
  var el = window.parent.document.querySelector('input[aria-label="__toggle__"]');
  if (el) {{
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
    setter.call(el, 'T'+Date.now());
    el.dispatchEvent(new Event('input', {{bubbles:true}}));
  }}
}}
</script>
""", unsafe_allow_html=True)

# ── Hidden control inputs (invisible, zero-height, drive routing) ─────────────
# These sit in the Streamlit main flow but are visually hidden.
# JS writes into them; Python reads on every rerun.

_ctrl_css = """
<style>
div[data-key="__nav_ctrl__"],
div[data-key="__tog_ctrl__"] {
    position:fixed; top:-9999px; left:-9999px;
    width:1px; height:1px; overflow:hidden; opacity:0; pointer-events:none;
}
/* Also hide via stTextInput wrapper */
div[data-testid="stTextInput"]:has(input[aria-label="__nav__"]),
div[data-testid="stTextInput"]:has(input[aria-label="__toggle__"]) {
    position:fixed !important; top:-9999px !important; left:-9999px !important;
    width:0 !important; height:0 !important; overflow:hidden !important;
}
</style>
"""
st.markdown(_ctrl_css, unsafe_allow_html=True)

nav_val = st.text_input("__nav__",    value="", key="__nav_ctrl__",    label_visibility="collapsed")
tog_val = st.text_input("__toggle__", value="", key="__tog_ctrl__",    label_visibility="collapsed")

# Process nav click
_valid_ids = [p for p,_,_ in NAV+SYS]
if nav_val and nav_val in _valid_ids and nav_val != active_page:
    st.session_state.active_page = nav_val
    st.session_state["__nav_ctrl__"] = ""
    st.rerun()

# Process toggle click
if tog_val and tog_val.startswith("T"):
    st.session_state.nav_expanded = not expanded
    st.session_state["__tog_ctrl__"] = ""
    st.rerun()

# ── Content wrapper — pushed right of the nav ─────────────────────────────────
st.markdown(f'<div class="tt-content" style="margin-left:{nav_w+8}px">', unsafe_allow_html=True)

# ── Logout button (top-right corner) ─────────────────────────────────────────
logout_col, _ = st.columns([1, 8])
with logout_col:
    if st.button("⎋ Logout", key="logout_main"):
        st.session_state.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="tt-topbar">
  <div>
    <div class="tt-page-title">{title}</div>
    <div class="tt-page-subtitle">{subtitle}</div>
  </div>
  <span class="tt-badge {'open' if is_market else 'closed'}">
    <span class="tt-dot"></span>
    {'NSE OPEN' if is_market else 'NSE CLOSED'}
    &nbsp;·&nbsp; {now_ist.strftime('%H:%M IST')}
  </span>
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
