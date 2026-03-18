"""ui/backtest_page.py — Validated backtest results with diagnostics."""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ui.components import page_section, empty_state, plotly_dark_layout, data_table

STRAT_COLORS = {
    "EMA Crossover": "#00D4FF", "RSI + MACD": "#00C87A",
    "Bollinger Bands": "#FFAA00", "Breakout": "#FF6600", "Volume Spike": "#AA44FF",
}
RELIABILITY_COLORS = {
    "VALID": "#00C87A", "LOW_CONFIDENCE": "#FFAA00", "VERY_LOW_CONFIDENCE": "#FF8800",
    "NO_TRADES": "#FF4455", "INSUFFICIENT_DATA": "#3A5070", "ERROR": "#FF4455", "": "#4A6080",
}


def render():
    page_section("Strategy Backtesting")
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#2A3D58;margin-bottom:16px">
      Initial capital: ₹10,000 · Commission: 0.1% per trade · Risk-free rate: 6.5%
    </div>""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1: sym_input = st.text_input("NSE Symbol", value="RELIANCE", key="bt_sym")
    with c2: period    = st.selectbox("Period", ["5y","10y","15y"], index=1, key="bt_period")
    with c3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_bt = st.button("Run Backtest →", type="primary", key="run_bt")
    with c4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        force  = st.checkbox("Force re-run", key="bt_force")

    if run_bt:
        symbol = sym_input.strip().upper()
        if not symbol.endswith(".NS"):
            symbol += ".NS"
        try:
            from data.fetcher import get_historical_data
            from analysis.backtester import run_all_backtests, get_best_strategy
            from data.cache import CacheManager
            cache = CacheManager()
            with st.spinner(f"Backtesting {symbol} over {period}..."):
                df = get_historical_data(symbol, period=period)
                if df is None or df.empty:
                    st.error("No data returned. Check the symbol.")
                    return
                years = len(df) / 252
                if years < 1:
                    st.error(f"Only {years:.1f} years of data — need at least 1 year.")
                    return
                results = run_all_backtests(symbol, df, force=force)
                best, score, reliable = get_best_strategy(results)
                cache.save_strategy_map(symbol, best, score)
                st.session_state.update({
                    "bt_results": results, "bt_best": best,
                    "bt_score": score, "bt_symbol": symbol,
                    "bt_reliable": reliable, "bt_years": round(years, 1),
                })
        except Exception as e:
            st.error(f"Backtest failed: {e}")
            import traceback; st.code(traceback.format_exc())
            return

    results  = st.session_state.get("bt_results")
    best     = st.session_state.get("bt_best")
    score    = st.session_state.get("bt_score")
    sym_lbl  = st.session_state.get("bt_symbol","")
    reliable = st.session_state.get("bt_reliable", False)
    years    = st.session_state.get("bt_years", 0)

    if results is None or results.empty:
        empty_state("No backtest results yet", "Enter a symbol and click Run Backtest")
        return

    # ── Data quality banner ────────────────────────────────────────────────────
    dq_color = "#00C87A" if years >= 8 else "#FFAA00" if years >= 5 else "#FF4455"
    st.markdown(f"""
    <div style="background:#080D18;border-radius:8px;padding:10px 16px;margin-bottom:14px;
                display:flex;gap:24px;align-items:center;flex-wrap:wrap">
      <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070">
        Data: <span style="color:{dq_color}">{years:.1f} years</span>
      </span>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070">
        Initial Capital: <span style="color:#00D4FF">₹10,000</span>
      </span>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070">
        Reliability: <span style="color:{'#00C87A' if reliable else '#FFAA00'}">
          {'VALIDATED' if reliable else 'LOW CONFIDENCE'}</span>
      </span>
    </div>""", unsafe_allow_html=True)

    # ── Best strategy banner ───────────────────────────────────────────────────
    bc = STRAT_COLORS.get(best, "#4A6080")
    if not reliable:
        st.warning(f"⚠ Best strategy '{best}' has low statistical confidence. Results may not be reliable.")

    st.markdown(f"""
    <div style="background:#0A1828;border:1px solid {bc}44;border-left:3px solid {bc};
                border-radius:12px;padding:18px 22px;margin-bottom:16px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:{bc};
                  text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px">
        Best Strategy — {sym_lbl.replace('.NS','')}
      </div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:20px;font-weight:600;
                  color:#E8EDF5">{best}</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#2A3D58;margin-top:4px">
        Composite score: {score:.3f}
        {'  ·  ✓ Statistically valid' if reliable else '  ·  ⚠ Low trade count'}
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Charts ─────────────────────────────────────────────────────────────────
    cL, cR = st.columns(2)
    with cL:
        page_section("Final Portfolio Value (from ₹10,000)")
        fig = go.Figure(go.Bar(
            x=results["strategy"], y=results["final_value"],
            marker=dict(color=[STRAT_COLORS.get(s,"#4A6080") for s in results["strategy"]],
                        opacity=0.85, line=dict(width=0)),
            text=[f"₹{v:,.0f}" for v in results["final_value"]],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
        ))
        fig = plotly_dark_layout(fig, height=250)
        fig.update_layout(yaxis_title="Final Value (₹)")
        st.plotly_chart(fig, use_container_width=True)

    with cR:
        page_section("CAGR %")
        colors_cagr = ["#00C87A" if v > 10 else "#FFAA00" if v > 0 else "#FF4455"
                       for v in results["cagr"]]
        fig2 = go.Figure(go.Bar(
            x=results["strategy"], y=results["cagr"],
            marker=dict(color=colors_cagr, opacity=0.85, line=dict(width=0)),
            text=[f"{v:.1f}%" for v in results["cagr"]],
            textposition="outside",
            textfont=dict(family="IBM Plex Mono", size=10, color="#4A6080"),
        ))
        fig2 = plotly_dark_layout(fig2, height=250)
        fig2.update_layout(yaxis_title="CAGR %")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Full validated metrics table ───────────────────────────────────────────
    page_section("Validated Metrics")
    rows = []
    for _, r in results.iterrows():
        strat = r.get("strategy","")
        rel   = str(r.get("reliability",""))
        rc    = RELIABILITY_COLORS.get(rel, "#4A6080")
        star  = " ★" if strat == best else ""
        cagr_c = "#00C87A" if r["cagr"] > 10 else "#FFAA00" if r["cagr"] > 0 else "#FF4455"
        diags = r.get("diagnostics", [])
        diag_str = "; ".join(diags[:2]) if isinstance(diags, list) and diags else ""
        rows.append([
            f'<span style="color:{STRAT_COLORS.get(strat,"#4A6080")};font-family:\'IBM Plex Mono\',monospace;font-size:12px">{strat}{star}</span>',
            f'<span style="color:{cagr_c};font-family:\'IBM Plex Mono\',monospace">{r["cagr"]:.2f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#8AA0BE">{r["sharpe"]:.3f}</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#FF6644">{r["max_drawdown"]:.1f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#8AA0BE">{r["win_rate"]:.1f}%</span>',
            f'<span style="font-family:\'IBM Plex Mono\',monospace;color:#3A5070">{int(r["total_trades"])}</span>',
            f'<code style="color:#C8D6E5">₹{r["final_value"]:,.0f}</code>',
            f'<span style="color:{rc};font-size:10px;font-family:\'IBM Plex Mono\',monospace">{rel}</span>',
        ])
    st.markdown(data_table(
        ["Strategy","CAGR","Sharpe","Max DD","Win Rate","Trades","Final Value","Reliability"],
        rows), unsafe_allow_html=True)

    # ── Diagnostics expander ───────────────────────────────────────────────────
    all_diags = [(r.get("strategy",""), r.get("diagnostics",[])) for _, r in results.iterrows()
                 if isinstance(r.get("diagnostics"), list) and r.get("diagnostics")]
    if all_diags:
        with st.expander("Validation Diagnostics"):
            for strat_name, diags in all_diags:
                for d in diags:
                    color = "#FFAA00" if "warn" in d.lower() or "low" in d.lower() else \
                            "#FF4455" if "error" in d.lower() or "no trades" in d.lower() else "#3A5070"
                    st.markdown(f"""
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                                color:{color};padding:4px 0;border-bottom:1px solid #0D1525">
                      <span style="color:#2A3D58">{strat_name}:</span> {d}
                    </div>""", unsafe_allow_html=True)
