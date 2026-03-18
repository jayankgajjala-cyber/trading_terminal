"""ui/portfolio_page.py"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from ui.components import (metric_card, page_section, signal_badge,
                            empty_state, plotly_dark_layout, data_table)


def render():
    # Try to import broker; graceful fallback for Streamlit Cloud demo
    try:
        from broker.zerodha import get_client
        from data.cache import CacheManager
        from config.settings import DEFAULT_MONTHLY_BUDGET, NIFTY50
        client = get_client()
        cache  = CacheManager()
        holdings = client.get_holdings()
    except Exception:
        client   = None
        holdings = pd.DataFrame()
        from config.settings import DEFAULT_MONTHLY_BUDGET, NIFTY50
        cache = None

    # ── Summary Metrics ────────────────────────────────────────────────────────
    page_section("Portfolio Summary")

    if not holdings.empty:
        has_cols = set(holdings.columns)
        inv_col  = "average_price" if "average_price" in has_cols else "avg_price"
        qty_col  = "quantity"
        cmp_col  = "last_price" if "last_price" in has_cols else "cmp"
        sym_col  = "tradingsymbol" if "tradingsymbol" in has_cols else "symbol"

        if inv_col in has_cols and qty_col in has_cols and cmp_col in has_cols:
            invested = (holdings[inv_col] * holdings[qty_col]).sum()
            current  = (holdings[cmp_col] * holdings[qty_col]).sum()
            pnl      = current - invested
            pnl_pct  = (pnl / invested * 100) if invested > 0 else 0
            pnl_sign = "pos" if pnl >= 0 else "neg"
        else:
            invested = current = pnl = pnl_pct = 0
            pnl_sign = "neu"

        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_card("Total Invested", f"₹{invested:,.0f}")
        with c2: metric_card("Current Value",  f"₹{current:,.0f}")
        with c3: metric_card("Total P&L",
                              f"₹{pnl:+,.0f}",
                              f"{pnl_pct:+.2f}%", pnl_sign)
        with c4: metric_card("Positions", str(len(holdings)))
    else:
        # Show paper portfolio if Zerodha not connected
        if cache:
            paper = cache.get_paper_portfolio()
        else:
            paper = pd.DataFrame()

        if not paper.empty:
            c1, c2, c3, c4 = st.columns(4)
            total_inv = paper["invested"].sum() if "invested" in paper.columns else 0
            with c1: metric_card("Paper Invested",  f"₹{total_inv:,.0f}")
            with c2: metric_card("Positions",       str(len(paper)))
            with c3: metric_card("Broker Status",   "NOT CONNECTED", "", "neg")
            with c4: metric_card("Mode",            "PAPER TRADE")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1: metric_card("Invested",    "₹0")
            with c2: metric_card("Current",     "₹0")
            with c3: metric_card("P&L",         "₹0")
            with c4: metric_card("Positions",   "0")
            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
            empty_state(
                "No holdings data",
                "Connect your Zerodha account from the Zerodha tab, or start paper trading."
            )
            return

    # ── Holdings Table ─────────────────────────────────────────────────────────
    page_section("Holdings")

    display_df = holdings.copy() if not holdings.empty else (
        paper.copy() if cache and not (cache.get_paper_portfolio().empty) else pd.DataFrame()
    )

    if not display_df.empty:
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=280,
        )

        # Allocation pie
        col_left, col_right = st.columns([1, 1])
        with col_left:
            sym_col = next(
                (c for c in ["tradingsymbol", "symbol"] if c in display_df.columns),
                display_df.columns[0]
            )
            val_col = next(
                (c for c in ["current_value", "last_price"] if c in display_df.columns),
                None
            )
            if val_col:
                fig = go.Figure(go.Pie(
                    labels=display_df[sym_col],
                    values=display_df[val_col],
                    hole=0.55,
                    marker=dict(
                        colors=["#00D4FF","#0066FF","#005588","#003D66","#002244",
                                "#001833","#001122","#000D1A","#000A14","#00070E"],
                        line=dict(color="#060A12", width=2)
                    ),
                    textinfo="label+percent",
                    textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
                ))
                fig = plotly_dark_layout(fig, "Allocation", height=300)
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        with col_right:
            page_section("Best Strategy per Stock")
            if cache:
                rows = []
                for sym in display_df.get(sym_col, pd.Series([])).tolist()[:15]:
                    best = cache.get_best_strategy(sym)
                    if best:
                        badge_color = {
                            "EMA Crossover":"#00D4FF","RSI + MACD":"#00C87A",
                            "Bollinger Bands":"#FFAA00","Breakout":"#FF6600",
                            "Volume Spike":"#AA44FF"
                        }.get(best, "#4A6080")
                        rows.append([
                            f'<code style="color:#C8D6E5">{sym.replace(".NS","")}</code>',
                            f'<span style="color:{badge_color};font-family:\'IBM Plex Mono\','
                            f'monospace;font-size:11px">{best}</span>'
                        ])
                if rows:
                    st.markdown(data_table(["Symbol", "Best Strategy"], rows),
                                unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="color:#2A3D58;font-family:\'IBM Plex Mono\','
                        'monospace;font-size:12px;padding:16px">Run weekly backtest to populate.</div>',
                        unsafe_allow_html=True
                    )

    # ── Budget Planner ─────────────────────────────────────────────────────────
    page_section("Monthly Budget Planner")

    col_a, col_b = st.columns([1, 2])
    with col_a:
        budget = st.number_input(
            "Monthly Budget (₹)",
            value=DEFAULT_MONTHLY_BUDGET,
            min_value=1000, step=1000,
            key="budget_input"
        )
        run_alloc = st.button("Generate Allocation →", type="primary")

    if run_alloc:
        try:
            from alerts.signal_engine import check_signals
            from broker.paper_trade import PaperTrader
            with st.spinner("Analysing signals..."):
                signals = check_signals(NIFTY50[:20], send_email=False)
            alloc = PaperTrader().suggest_allocation(budget=budget, signals=signals)
            with col_b:
                if not alloc.empty:
                    st.dataframe(alloc, use_container_width=True, hide_index=True)
                else:
                    empty_state("No active BUY signals", "Try during market hours 9:15–15:30 IST")
        except Exception as e:
            st.error(f"Signal analysis error: {e}")
