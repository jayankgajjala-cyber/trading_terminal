"""ui/signals_page.py — Live signals with deep analysis, bias detection, per-strategy breakdown."""
import streamlit as st
import pandas as pd
from ui.components import page_section, signal_badge, confidence_bar, empty_state, data_table


def render():
    try:
        from alerts.signal_engine import check_signals, is_market_hours
        from analysis.technical import check_signal_bias
        from config.settings import NIFTY50
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    # ── Watchlist + controls ──────────────────────────────────────────────────
    page_section("Watchlist Configuration")

    # Portfolio symbols as default
    try:
        from data.portfolio import load_csv
        df_port, _ = load_csv()
        if df_port is not None and not df_port.empty:
            port_syms = [s.replace(".NS","") for s in df_port["symbol"].tolist()[:20]]
        else:
            port_syms = [s.replace(".NS","") for s in NIFTY50[:20]]
    except Exception:
        port_syms = [s.replace(".NS","") for s in NIFTY50[:20]]

    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        watchlist_raw = st.text_area(
            "Symbols (comma-separated, no .NS needed)",
            value=",".join(port_syms),
            height=70, key="watchlist_input",
        )
    with col2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_btn = st.button("Run Analysis →", type="primary", key="run_signals")
    with col3:
        mkt_open = is_market_hours()
        st.markdown(f"""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;margin-top:32px;
                    color:{'#00C87A' if mkt_open else '#FFAA00'};letter-spacing:0.05em">
          ● {'MARKET OPEN' if mkt_open else 'MARKET CLOSED'}
        </div>""", unsafe_allow_html=True)

    symbols = [s.strip().upper() + ".NS" for s in watchlist_raw.split(",") if s.strip()]

    if run_btn:
        with st.spinner(f"Running deep analysis on {len(symbols)} symbols..."):
            try:
                signals = check_signals(symbols, send_email=False)
                st.session_state["last_signals"]    = signals
                st.session_state["signals_checked"] = True
            except Exception as e:
                st.error(f"Signal check failed: {e}")
                import traceback; st.code(traceback.format_exc())
                return

    signals = st.session_state.get("last_signals", [])
    if not signals:
        empty_state("No signals yet", "Click 'Run Analysis' to analyse your watchlist")
        return

    # ── Bias detection ─────────────────────────────────────────────────────────
    bias = check_signal_bias(signals)
    if bias.get("bias"):
        st.markdown(f"""
        <div style="background:#1A0A00;border:1px solid #FFAA0055;border-radius:8px;
                    padding:12px 16px;margin-bottom:16px;font-family:'IBM Plex Mono',monospace;
                    font-size:12px;color:#FFAA00">
          {bias['message']}
        </div>""", unsafe_allow_html=True)

    # ── Summary metrics ────────────────────────────────────────────────────────
    page_section("Signal Summary")

    buy   = [s for s in signals if s["signal"] == "BUY"]
    sell  = [s for s in signals if s["signal"] == "SELL"]
    hold  = [s for s in signals if s["signal"] == "HOLD"]
    total = len(signals)

    def _pct(n): return f"{n/total*100:.0f}% of scan" if total else "—"

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, pct_str, color in [
        (c1, "BUY Signals",  len(buy),  _pct(len(buy)),  "#00C87A"),
        (c2, "SELL Signals", len(sell), _pct(len(sell)), "#FF4455"),
        (c3, "HOLD",         len(hold), _pct(len(hold)), "#FFAA00"),
        (c4, "Avg Confidence",
             f"{sum(s.get('confidence',0) for s in signals)/total*100:.0f}%" if total else "—",
             f"{total} scanned", "#00D4FF"),
    ]:
        with col:
            st.markdown(f"""
            <div class="tt-metric">
              <div class="tt-metric-label">{lbl}</div>
              <div class="tt-metric-value" style="color:{color}">{val}</div>
              <div class="tt-metric-delta neu">{pct_str}</div>
            </div>""", unsafe_allow_html=True)

    # ── Filter + sort ──────────────────────────────────────────────────────────
    page_section("Signal Details")
    fc1, fc2, fc3 = st.columns([1, 1, 3])
    with fc1:
        filter_sig = st.selectbox("Filter", ["ALL","BUY","SELL","HOLD"], key="sig_filter")
    with fc2:
        sort_by = st.selectbox("Sort", ["Confidence ↓","Signal","Symbol"], key="sig_sort")

    filtered = [s for s in signals if filter_sig == "ALL" or s["signal"] == filter_sig]
    sort_map = {
        "Confidence ↓": lambda x: -x.get("confidence", 0),
        "Signal":       lambda x: {"BUY":0,"SELL":1,"HOLD":2}.get(x["signal"],3),
        "Symbol":       lambda x: x["symbol"],
    }
    filtered.sort(key=sort_map.get(sort_by, lambda x: 0))

    # ── Signal table ───────────────────────────────────────────────────────────
    rows = []
    for s in filtered:
        sym    = s["symbol"].replace(".NS","")
        sig    = signal_badge(s["signal"])
        price  = f'<code style="color:#C8D6E5">₹{s.get("price",0):,.2f}</code>'
        strat  = f'<span style="color:#3A5070;font-size:11px">{s.get("best_strategy","—")}</span>'
        reason = f'<span style="color:#2A3D58;font-size:11px">{s.get("reason","")[:65]}</span>'
        conf   = confidence_bar(s.get("confidence", 0))
        dq_c   = {"GOOD":"#00C87A","MODERATE":"#FFAA00","LOW":"#FF8800","POOR":"#FF4455",
                  "INSUFFICIENT":"#3A5070","NO_DATA":"#2A3D58"}.get(s.get("data_quality",""), "#3A5070")
        dq     = f'<span style="color:{dq_c};font-size:10px;font-family:\'IBM Plex Mono\',monospace">{s.get("data_quality","—")}</span>'
        warn   = s.get("warning","")
        warn_html = (f'<span style="color:#FFAA00;font-size:10px">⚠</span>' if warn else "")

        rows.append([
            f'<code style="color:#E8EDF5;font-size:13px">{sym}</code>{warn_html}',
            sig, price, strat, reason, conf, dq,
            f'<span style="color:#1A2D40;font-size:10px;font-family:\'IBM Plex Mono\',monospace">{s.get("years",0):.1f}y</span>'
        ])

    st.markdown(
        data_table(["Symbol","Signal","Price","Best Strategy","Reason","Confidence","Data","History"], rows),
        unsafe_allow_html=True
    )

    # ── Expandable per-strategy breakdown ─────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    with st.expander("Per-strategy breakdown (click to expand)"):
        for s in filtered[:10]:
            sym = s["symbol"].replace(".NS","")
            strats = s.get("strategies", {})
            if not strats:
                continue
            st.markdown(f"""
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070;
                        text-transform:uppercase;letter-spacing:0.08em;padding:8px 0 4px;
                        border-top:1px solid #0D1525;margin-top:8px">{sym}</div>""",
                        unsafe_allow_html=True)
            rows2 = []
            for strat_name, res in strats.items():
                sc = {"BUY":"#00C87A","SELL":"#FF4455","HOLD":"#FFAA00"}.get(res["signal"],"#4A6080")
                rows2.append([
                    f'<span style="color:#8AA0BE;font-size:12px">{strat_name}</span>',
                    f'<span style="color:{sc};font-weight:600;font-family:\'IBM Plex Mono\',monospace;font-size:11px">{res["signal"]}</span>',
                    confidence_bar(res.get("score", 0)),
                    f'<span style="color:#2A3D58;font-size:11px">{res.get("reason","")[:70]}</span>',
                ])
            st.markdown(data_table(["Strategy","Signal","Score","Reason"], rows2), unsafe_allow_html=True)

    # ── Deep analysis context ──────────────────────────────────────────────────
    if any(s.get("deep") for s in filtered[:5]):
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("Deep market context"):
            da_rows = []
            for s in filtered[:8]:
                da = s.get("deep", {})
                if not da:
                    continue
                sym   = s["symbol"].replace(".NS","")
                trend = f'{da.get("short_trend","?")}/{da.get("mid_trend","?")}/{da.get("long_trend","?")}'
                aligned = "✓" if da.get("trend_aligned") else "—"
                roc   = da.get("momentum_roc14", 0)
                roc_c = "#00C87A" if roc > 1 else "#FF4455" if roc < -1 else "#4A6080"
                da_rows.append([
                    f'<code style="color:#E8EDF5">{sym}</code>',
                    f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:#8AA0BE">{trend}</span>',
                    f'<span style="color:#3A5070">{aligned}</span>',
                    f'<span style="color:{roc_c};font-family:\'IBM Plex Mono\',monospace;font-size:11px">{roc:+.1f}%</span>',
                    f'<span style="color:#3A5070;font-size:11px">{da.get("pct_from_52w_high",0):+.1f}%</span>',
                    f'<span style="color:#2A3D58;font-size:11px">{da.get("annualised_vol",0):.1f}%</span>',
                ])
            if da_rows:
                st.markdown(
                    data_table(["Symbol","Trend (S/M/L)","Aligned","14D ROC","From 52W H","Ann.Vol"], da_rows),
                    unsafe_allow_html=True
                )
