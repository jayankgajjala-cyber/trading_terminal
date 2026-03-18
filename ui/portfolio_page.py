"""ui/portfolio_page.py — CSV-first portfolio with Zerodha fallback."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ui.components import (page_section, empty_state, plotly_dark_layout,
                            data_table, signal_badge)


def render():
    try:
        from data.portfolio import load_csv, get_symbols, create_sample_file, SAMPLE_CSV
        from data.fetcher import get_historical_data
        from config.settings import DEFAULT_MONTHLY_BUDGET, NIFTY50
        from data.cache import CacheManager
        cache = CacheManager()
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    # ── Portfolio source ────────────────────────────────────────────────────────
    page_section("Portfolio Source")
    src_col, help_col = st.columns([3, 1])
    with src_col:
        uploaded = st.file_uploader(
            "Upload portfolio CSV",
            type=["csv"],
            key="port_csv_upload",
            help="Columns: symbol, qty, avg_price, buy_date"
        )
    with help_col:
        if st.button("Create sample CSV", key="create_sample"):
            create_sample_file()
            st.success("Created data/portfolio.csv")
        with st.expander("CSV format"):
            st.code(SAMPLE_CSV, language="csv")

    # Load portfolio
    df_port, err = load_csv(uploaded)

    if err:
        st.warning(err)
        # Try Zerodha fallback
        try:
            from broker.zerodha import get_client
            client = get_client()
            if client.connected:
                st.info("Using Zerodha live holdings as fallback.")
                holdings = client.get_holdings()
            else:
                holdings = pd.DataFrame()
        except Exception:
            holdings = pd.DataFrame()

        if holdings.empty:
            empty_state(
                "No portfolio loaded",
                "Upload a CSV file above, or connect Zerodha in the Zerodha tab."
            )
            return
        # Use Zerodha holdings as df_port
        df_port = holdings.rename(columns={
            "tradingsymbol": "symbol",
            "quantity": "qty",
            "average_price": "avg_price",
        }) if not holdings.empty else df_port
    else:
        st.success(f"Portfolio loaded: {len(df_port)} positions")

    # Show preview
    with st.expander(f"Portfolio preview ({len(df_port)} rows)"):
        st.dataframe(df_port, use_container_width=True, hide_index=True, height=200)

    symbols = get_symbols(df_port)

    # ── Live price enrichment ───────────────────────────────────────────────────
    page_section("Holdings Summary")

    @st.cache_data(ttl=300, show_spinner=False)
    def _get_price(sym):
        df = get_historical_data(sym, period="5d")
        return round(df["Close"].iloc[-1], 2) if not df.empty else None

    rows = []
    total_invested = 0.0
    total_current  = 0.0

    for _, row in df_port.iterrows():
        sym      = row.get("symbol", "")
        qty      = float(row.get("qty", 0) or 0)
        avg_p    = float(row.get("avg_price", 0) or 0)
        cmp      = _get_price(sym)
        if cmp is None:
            cmp = avg_p

        invested = qty * avg_p
        current  = qty * cmp
        pnl      = current - invested
        pnl_pct  = (pnl / invested * 100) if invested > 0 else 0
        pnl_c    = "#00C87A" if pnl >= 0 else "#FF4455"

        total_invested += invested
        total_current  += current

        best = cache.get_best_strategy(sym) or "—"
        rows.append([
            f'<code style="color:#E8EDF5">{sym.replace(".NS","")}</code>',
            f'<span style="color:#8AA0BE;font-family:\'IBM Plex Mono\',monospace">{int(qty)}</span>',
            f'<code>₹{avg_p:,.2f}</code>',
            f'<code style="color:#C8D6E5">₹{cmp:,.2f}</code>',
            f'<code style="color:#8AA0BE">₹{invested:,.0f}</code>',
            f'<code style="color:{pnl_c}">₹{pnl:+,.0f} ({pnl_pct:+.1f}%)</code>',
            f'<span style="color:#3A5070;font-size:11px">{best}</span>',
        ])

    total_pnl     = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, color in [
        (c1, "Invested",   f"₹{total_invested:,.0f}",  "#E8EDF5"),
        (c2, "Current",    f"₹{total_current:,.0f}",   "#E8EDF5"),
        (c3, "Total P&L",  f"₹{total_pnl:+,.0f}",     "#00C87A" if total_pnl >= 0 else "#FF4455"),
        (c4, "Return",     f"{total_pnl_pct:+.2f}%",  "#00C87A" if total_pnl >= 0 else "#FF4455"),
    ]:
        with col:
            st.markdown(f"""
            <div class="tt-metric">
              <div class="tt-metric-label">{lbl}</div>
              <div class="tt-metric-value" style="color:{color};font-size:18px">{val}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown(data_table(["Symbol","Qty","Avg Price","CMP","Invested","P&L","Best Strategy"], rows),
                unsafe_allow_html=True)

    # ── Allocation pie ──────────────────────────────────────────────────────────
    if len(df_port) > 1:
        page_section("Allocation")
        col_pie, col_alloc = st.columns([1, 1])
        with col_pie:
            vals = []
            lbls = []
            for _, row in df_port.iterrows():
                sym  = row.get("symbol","")
                qty  = float(row.get("qty",0) or 0)
                avg  = float(row.get("avg_price",0) or 0)
                vals.append(qty * avg)
                lbls.append(sym.replace(".NS",""))
            fig = go.Figure(go.Pie(
                labels=lbls, values=vals, hole=0.55,
                marker=dict(colors=["#00D4FF","#0066FF","#005588","#003D66",
                                     "#002244","#001833","#001122","#000D1A"],
                            line=dict(color="#060A12", width=2)),
                textinfo="label+percent",
                textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
            ))
            fig = plotly_dark_layout(fig, "Portfolio Allocation", height=280)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── Budget planner ──────────────────────────────────────────────────────────
    page_section("Monthly Budget Planner")
    bc1, bc2 = st.columns([1, 2])
    with bc1:
        budget    = st.number_input("Monthly Budget (₹)", value=DEFAULT_MONTHLY_BUDGET,
                                     min_value=1000, step=1000, key="port_budget")
        run_alloc = st.button("Suggest Allocation →", type="primary", key="port_alloc")
    if run_alloc:
        with st.spinner("Generating allocation from live signals..."):
            try:
                from alerts.signal_engine import check_signals
                sigs   = check_signals(symbols[:20], send_email=False)
                buys   = [s for s in sigs if s["signal"] == "BUY" and s.get("confidence",0) >= 0.40]
                if buys:
                    total_conf = sum(s["confidence"] for s in buys)
                    alloc_rows = []
                    for s in sorted(buys, key=lambda x: -x["confidence"])[:8]:
                        weight = s["confidence"] / total_conf
                        amount = round(budget * weight, -1)
                        df_tmp = get_historical_data(s["symbol"], period="5d")
                        price  = round(df_tmp["Close"].iloc[-1], 2) if not df_tmp.empty else 0
                        shares = int(amount // price) if price > 0 else 0
                        alloc_rows.append({
                            "Symbol":       s["symbol"].replace(".NS",""),
                            "Allocation ₹": f"₹{amount:,.0f}",
                            "~Shares":      shares,
                            "Price":        f"₹{price:,.2f}",
                            "Confidence":   f"{s['confidence']*100:.0f}%",
                            "Reason":       s.get("reason","")[:50],
                        })
                    with bc2:
                        st.dataframe(pd.DataFrame(alloc_rows),
                                     use_container_width=True, hide_index=True)
                else:
                    with bc2:
                        st.info("No active BUY signals with sufficient confidence right now.")
            except Exception as e:
                st.error(f"Allocation error: {e}")
