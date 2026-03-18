"""ui/signals_page.py"""
import streamlit as st
import pandas as pd
from ui.components import page_section, signal_badge, confidence_bar, empty_state, data_table


def render():
    try:
        from alerts.signal_engine import check_signals, is_market_hours
        from config.settings import NIFTY50
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    # ── Watchlist input ────────────────────────────────────────────────────────
    page_section("Watchlist Configuration")

    col1, col2 = st.columns([3, 1])
    with col1:
        default_syms = ",".join([s.replace(".NS", "") for s in NIFTY50[:20]])
        watchlist_raw = st.text_area(
            "Symbols (comma-separated)",
            value=default_syms,
            height=70,
            key="watchlist_input",
            help="Enter NSE symbols without .NS suffix"
        )
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_btn = st.button("Run Analysis →", type="primary", key="run_signals")
        mkt_open = is_market_hours()
        status_color = "#00C87A" if mkt_open else "#FFAA00"
        st.markdown(f"""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                    color:{status_color};margin-top:8px;letter-spacing:0.05em">
          ● {'MARKET OPEN' if mkt_open else 'MARKET CLOSED'}
        </div>""", unsafe_allow_html=True)

    symbols = [s.strip().upper() + ".NS" for s in watchlist_raw.split(",") if s.strip()]

    if run_btn:
        with st.spinner(f"Analysing {len(symbols)} symbols..."):
            try:
                signals = check_signals(symbols, send_email=False)
                st.session_state["last_signals"] = signals
            except Exception as e:
                st.error(f"Signal check failed: {e}")
                return

    signals = st.session_state.get("last_signals", [])

    if not signals:
        empty_state(
            "No signals yet",
            "Click 'Run Analysis' to check your watchlist"
        )
        return

    # ── Summary metrics ────────────────────────────────────────────────────────
    page_section("Signal Summary")

    buy  = [s for s in signals if s["signal"] == "BUY"]
    sell = [s for s in signals if s["signal"] == "SELL"]
    hold = [s for s in signals if s["signal"] == "HOLD"]
    total = len(signals)

    c1, c2, c3, c4 = st.columns(4)

    def _pct(n): return f"{n/total*100:.0f}% of scan" if total else "—"

    with c1:
        st.markdown(f"""
        <div class="tt-metric">
          <div class="tt-metric-label">BUY Signals</div>
          <div class="tt-metric-value" style="color:#00C87A">{len(buy)}</div>
          <div class="tt-metric-delta pos">{_pct(len(buy))}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="tt-metric">
          <div class="tt-metric-label">SELL Signals</div>
          <div class="tt-metric-value" style="color:#FF4455">{len(sell)}</div>
          <div class="tt-metric-delta neg">{_pct(len(sell))}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="tt-metric">
          <div class="tt-metric-label">HOLD</div>
          <div class="tt-metric-value" style="color:#FFAA00">{len(hold)}</div>
          <div class="tt-metric-delta neu">{_pct(len(hold))}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        avg_conf = sum(s.get("confidence", 0) for s in signals) / total if total else 0
        st.markdown(f"""
        <div class="tt-metric">
          <div class="tt-metric-label">Avg Confidence</div>
          <div class="tt-metric-value">{avg_conf*100:.0f}%</div>
          <div class="tt-metric-delta neu">{total} symbols scanned</div>
        </div>""", unsafe_allow_html=True)

    # ── Full signal table ──────────────────────────────────────────────────────
    page_section("Signal Details")

    # Filter controls
    fcol1, fcol2, _ = st.columns([1, 1, 3])
    with fcol1:
        filter_sig = st.selectbox("Filter", ["ALL", "BUY", "SELL", "HOLD"], key="sig_filter")
    with fcol2:
        sort_by = st.selectbox("Sort by", ["Signal", "Confidence", "Symbol"], key="sig_sort")

    filtered = [s for s in signals if filter_sig == "ALL" or s["signal"] == filter_sig]
    sort_key = {
        "Signal":     lambda x: {"BUY": 0, "SELL": 1, "HOLD": 2}.get(x["signal"], 3),
        "Confidence": lambda x: -x.get("confidence", 0),
        "Symbol":     lambda x: x["symbol"],
    }.get(sort_by, lambda x: 0)
    filtered.sort(key=sort_key)

    rows = []
    for s in filtered:
        sym = s["symbol"].replace(".NS", "")
        sig = signal_badge(s["signal"])
        price = f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#C8D6E5">₹{s.get("price",0):,.2f}</span>'
        strat = f'<span style="color:#3A5070;font-size:12px">{s.get("best_strategy","")}</span>'
        reason = f'<span style="color:#2A3D58;font-size:11px">{s.get("reason","")[:65]}</span>'
        conf = confidence_bar(s.get("confidence", 0))
        ts = f'<span style="color:#1A2D40;font-family:\'IBM Plex Mono\',monospace;font-size:10px">{s.get("timestamp","")}</span>'
        rows.append([
            f'<code style="color:#E8EDF5;font-size:13px">{sym}</code>',
            sig, price, strat, reason, conf, ts
        ])

    st.markdown(
        data_table(["Symbol", "Signal", "Price", "Strategy", "Reason", "Confidence", "Time"], rows),
        unsafe_allow_html=True
    )
