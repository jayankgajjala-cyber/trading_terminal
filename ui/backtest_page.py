"""ui/backtest_page.py"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ui.components import page_section, empty_state, plotly_dark_layout, data_table


def render():
    page_section("Strategy Backtesting")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sym_input = st.text_input("NSE Symbol", value="RELIANCE", key="bt_sym")
    with col2:
        period = st.selectbox("Period", ["2y", "5y", "10y"], index=2, key="bt_period")
    with col3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_bt = st.button("Run Backtest →", type="primary", key="run_bt")

    force = st.checkbox("Force re-run (ignore cache)", key="bt_force")

    if run_bt:
        symbol = sym_input.strip().upper() + ".NS"
        try:
            from data.fetcher import get_historical_data
            from analysis.backtester import run_all_backtests, get_best_strategy
            from data.cache import CacheManager
            cache = CacheManager()

            with st.spinner(f"Backtesting {symbol} over {period}…"):
                df = get_historical_data(symbol, period=period)
                if df.empty:
                    st.error("No data. Check the symbol.")
                    return
                results = run_all_backtests(symbol, df, force=force)
                best, score = get_best_strategy(results)
                cache.save_strategy_map(symbol, best, score)
                st.session_state["bt_results"] = results
                st.session_state["bt_best"]    = best
                st.session_state["bt_score"]   = score
                st.session_state["bt_symbol"]  = symbol
        except Exception as e:
            st.error(f"Backtest failed: {e}")
            return

    results = st.session_state.get("bt_results")
    best    = st.session_state.get("bt_best")
    score   = st.session_state.get("bt_score")
    sym_lbl = st.session_state.get("bt_symbol", "")

    if results is None or results.empty:
        empty_state("No backtest results yet", "Enter a symbol and click Run Backtest")
        return

    # ── Best strategy banner ───────────────────────────────────────────────────
    strategy_colors = {
        "EMA Crossover":   "#00D4FF",
        "RSI + MACD":      "#00C87A",
        "Bollinger Bands": "#FFAA00",
        "Breakout":        "#FF6600",
        "Volume Spike":    "#AA44FF",
    }
    bc = strategy_colors.get(best, "#4A6080")

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0A1828,#080D18);border:1px solid {bc}33;
                border-radius:12px;padding:20px 24px;margin:12px 0 20px;
                border-left:3px solid {bc}">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:{bc};
                  letter-spacing:0.1em;text-transform:uppercase;margin-bottom:8px">
        Best Strategy — {sym_lbl.replace('.NS','')}
      </div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;
                  color:#E8EDF5">{best}</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#2A3D58;
                  margin-top:6px">Composite score: {score:.3f}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Charts side by side ────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        page_section("CAGR by Strategy")
        fig_cagr = go.Figure(go.Bar(
            x=results["strategy"],
            y=results["cagr"],
            marker=dict(
                color=[strategy_colors.get(s, "#4A6080") for s in results["strategy"]],
                opacity=0.85,
                line=dict(width=0),
            ),
            text=[f"{v:.1f}%" for v in results["cagr"]],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
        ))
        fig_cagr = plotly_dark_layout(fig_cagr, height=260)
        fig_cagr.update_layout(yaxis_title="CAGR %", xaxis_tickfont=dict(size=10))
        st.plotly_chart(fig_cagr, use_container_width=True)

    with col_right:
        page_section("Sharpe Ratio")
        fig_sharpe = go.Figure(go.Bar(
            x=results["strategy"],
            y=results["sharpe"].fillna(0),
            marker=dict(
                color=[strategy_colors.get(s, "#4A6080") for s in results["strategy"]],
                opacity=0.85, line=dict(width=0),
            ),
            text=[f"{v:.2f}" for v in results["sharpe"].fillna(0)],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
        ))
        fig_sharpe = plotly_dark_layout(fig_sharpe, height=260)
        fig_sharpe.update_layout(yaxis_title="Sharpe Ratio")
        st.plotly_chart(fig_sharpe, use_container_width=True)

    # ── Full metrics table ─────────────────────────────────────────────────────
    page_section("Full Metrics")

    rows = []
    for _, r in results.iterrows():
        strat = r["strategy"]
        bc2 = strategy_colors.get(strat, "#4A6080")
        star = " ★" if strat == best else ""
        rows.append([
            f'<span style="color:{bc2};font-family:\'IBM Plex Mono\',monospace;font-size:12px">{strat}{star}</span>',
            f'<span style="color:{"#00C87A" if r["cagr"]>10 else "#FFAA00" if r["cagr"]>0 else "#FF4455"};'
            f'font-family:\'IBM Plex Mono\',monospace">{r["cagr"]:.2f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#8AA0BE">{r["sharpe"]:.3f}</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#FF6644">{r["max_drawdown"]:.1f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#8AA0BE">{r["win_rate"]:.1f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#3A5070">{int(r["total_trades"])}</span>',
        ])

    st.markdown(
        data_table(["Strategy", "CAGR", "Sharpe", "Max DD", "Win Rate", "Trades"], rows),
        unsafe_allow_html=True
    )
