"""ui/paper_trade_page.py"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ui.components import page_section, empty_state, plotly_dark_layout, data_table, signal_badge


def render():
    try:
        from broker.paper_trade import PaperTrader
        from data.cache import CacheManager
        from config.settings import DEFAULT_MONTHLY_BUDGET, NIFTY50
        cache  = CacheManager()
        trader = PaperTrader()
    except Exception as e:
        st.error(f"Module load error: {e}")
        return

    # ── Portfolio Summary ──────────────────────────────────────────────────────
    page_section("Paper Portfolio")

    with st.spinner("Loading portfolio..."):
        df = trader.get_portfolio_summary()

    if df.empty:
        empty_state("No paper positions", "Use the Trade panel below to place your first order")
    else:
        total_inv  = df["Invested"].sum()
        total_val  = df["Current Value"].sum()
        total_pnl  = df["P&L"].sum()
        pnl_pct    = (total_pnl / total_inv * 100) if total_inv > 0 else 0
        pnl_sign   = "pos" if total_pnl >= 0 else "neg"

        c1, c2, c3, c4 = st.columns(4)
        for col, label, val in [
            (c1, "Invested",    f"₹{total_inv:,.0f}"),
            (c2, "Value",       f"₹{total_val:,.0f}"),
            (c3, "P&L",         f"₹{total_pnl:+,.0f}"),
            (c4, "Return",      f"{pnl_pct:+.2f}%"),
        ]:
            with col:
                color = ("#00C87A" if total_pnl >= 0 else "#FF4455") if label in ("P&L","Return") else "#E8EDF5"
                st.markdown(f"""
                <div class="tt-metric">
                  <div class="tt-metric-label">{label}</div>
                  <div class="tt-metric-value" style="color:{color}">{val}</div>
                </div>""", unsafe_allow_html=True)

        # P&L bar chart
        col_left, col_right = st.columns([3, 2])
        with col_left:
            page_section("P&L by Position")
            colors = ["#00C87A" if v >= 0 else "#FF4455" for v in df["P&L %"]]
            fig = go.Figure(go.Bar(
                x=df["Symbol"], y=df["P&L %"],
                marker=dict(color=colors, opacity=0.85, line=dict(width=0)),
                text=[f"{v:+.1f}%" for v in df["P&L %"]],
                textposition="outside",
                textfont=dict(family="IBM Plex Mono", size=10),
            ))
            fig = plotly_dark_layout(fig, height=240)
            fig.update_layout(yaxis_title="P&L %", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            page_section("Positions Table")
            rows = []
            for _, r in df.iterrows():
                pnl_c = "#00C87A" if r["P&L"] >= 0 else "#FF4455"
                rows.append([
                    f'<code style="color:#E8EDF5">{r["Symbol"].replace(".NS","")}</code>',
                    f'<span style="color:#8AA0BE;font-family:\'IBM Plex Mono\',monospace">{int(r["Qty"])}</span>',
                    f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#C8D6E5">₹{r["CMP"]:,.2f}</span>',
                    f'<span style="font-family:\'IBM Plex Mono\',monospace;color:{pnl_c}">{r["P&L %"]:+.1f}%</span>',
                ])
            st.markdown(data_table(["Symbol","Qty","CMP","P&L %"], rows), unsafe_allow_html=True)

    # ── Trade Panel ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    page_section("Place Trade")

    col_buy, col_sell = st.columns(2)

    with col_buy:
        st.markdown("""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#00C87A;
                    letter-spacing:0.1em;text-transform:uppercase;margin-bottom:12px">
          ▲ Buy Order
        </div>""", unsafe_allow_html=True)
        buy_sym = st.text_input("Symbol", placeholder="e.g. RELIANCE", key="buy_sym").upper().strip()
        buy_amt = st.number_input("Amount (₹)", min_value=100.0, value=float(DEFAULT_MONTHLY_BUDGET),
                                   step=500.0, key="buy_amt")
        if st.button("Execute Buy →", type="primary", key="exec_buy"):
            if buy_sym:
                with st.spinner("Executing..."):
                    try:
                        r = trader.buy(buy_sym + ".NS", buy_amt)
                        if r["success"]:
                            st.success(r["message"])
                        else:
                            st.error(r["message"])
                    except Exception as e:
                        st.error(str(e))

    with col_sell:
        st.markdown("""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#FF4455;
                    letter-spacing:0.1em;text-transform:uppercase;margin-bottom:12px">
          ▼ Sell Order
        </div>""", unsafe_allow_html=True)
        try:
            paper_port = cache.get_paper_portfolio()
            hold_syms  = paper_port["symbol"].tolist() if not paper_port.empty else []
        except Exception:
            hold_syms = []

        if hold_syms:
            sell_sym = st.selectbox("Symbol", hold_syms, key="sell_sym")
            sell_all = st.checkbox("Sell entire position", value=True, key="sell_all_chk")
            sell_qty = None
            if not sell_all:
                max_q = int(paper_port[paper_port["symbol"] == sell_sym]["quantity"].values[0])
                sell_qty = st.number_input("Qty", min_value=1, max_value=max_q,
                                            value=1, key="sell_qty")
            if st.button("Execute Sell →", key="exec_sell"):
                with st.spinner("Executing..."):
                    try:
                        r = trader.sell(sell_sym, qty=sell_qty)
                        if r["success"]:
                            pnl_col = "success" if r["pnl"] >= 0 else "error"
                            getattr(st, pnl_col)(r["message"])
                        else:
                            st.error(r["message"])
                    except Exception as e:
                        st.error(str(e))
        else:
            st.markdown('<div style="color:#1A2D40;font-size:13px;padding:16px 0">No positions to sell.</div>',
                        unsafe_allow_html=True)

    # ── Budget Allocation ──────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    page_section("Signal-Based Allocation")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        budget = st.number_input("Budget (₹)", min_value=1000, value=DEFAULT_MONTHLY_BUDGET,
                                  step=1000, key="pt_budget")
        run_alloc = st.button("Suggest Allocation →", key="suggest_alloc")

    if run_alloc:
        try:
            from alerts.signal_engine import check_signals
            with st.spinner("Analysing signals..."):
                sigs = check_signals(NIFTY50[:25], send_email=False)
            alloc = trader.suggest_allocation(budget=budget, signals=sigs)
            with col_b:
                if not alloc.empty:
                    st.dataframe(alloc, use_container_width=True, hide_index=True)
                    if st.button("Execute All Buys", key="exec_all_buys"):
                        for _, row in alloc.iterrows():
                            sym = row["Symbol"]
                            if ".NS" not in sym:
                                sym += ".NS"
                            r = trader.buy(sym, row["Allocation (₹)"])
                            icon = "✅" if r["success"] else "❌"
                            st.markdown(f"<div style='font-family:IBM Plex Mono,monospace;font-size:12px'>"
                                        f"{icon} {r['message']}</div>", unsafe_allow_html=True)
                else:
                    empty_state("No BUY signals", "Try during market hours 9:15–15:30 IST")
        except Exception as e:
            st.error(str(e))

    # ── Trade History ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    page_section("Trade History")

    try:
        trades = cache.get_paper_trades(limit=50)
        if not trades.empty:
            trades["timestamp"] = pd.to_datetime(trades["timestamp"], unit="s").dt.strftime("%d %b %Y %H:%M")
            st.dataframe(
                trades.rename(columns={"symbol":"Symbol","action":"Action","quantity":"Qty",
                                        "price":"Price","timestamp":"Time","pnl":"P&L"}),
                use_container_width=True, hide_index=True, height=240
            )
        else:
            st.markdown('<div style="color:#1A2D40;font-size:12px;padding:12px 0">No trades yet.</div>',
                        unsafe_allow_html=True)
    except Exception:
        st.markdown('<div style="color:#1A2D40;font-size:12px;padding:12px 0">Trade history unavailable.</div>',
                    unsafe_allow_html=True)
