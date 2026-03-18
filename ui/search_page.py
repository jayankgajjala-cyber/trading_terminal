"""ui/search_page.py"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from ui.components import (page_section, signal_badge, confidence_bar,
                            empty_state, plotly_dark_layout, data_table)


def render():
    # ── Search bar ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        sym_input = st.text_input(
            "NSE Symbol", placeholder="e.g.  RELIANCE  ·  TCS  ·  BAJFINANCE",
            key="search_sym"
        )
    with col2:
        period = st.selectbox("Period", ["1y","2y","5y","10y"], index=2, key="search_period")
    with col3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        search_btn = st.button("Analyse →", type="primary", key="run_search")

    if not sym_input.strip() and not st.session_state.get("search_result"):
        empty_state(
            "Enter any NSE symbol to begin",
            "Full technical + fundamental + backtest + 24-month projection"
        )
        return

    if search_btn and sym_input.strip():
        symbol    = sym_input.strip().upper()
        yf_symbol = symbol + ".NS"
        try:
            from data.fetcher import get_historical_data, get_fundamental_data
            from analysis.technical import run_all_strategies, get_consensus, deep_analysis
            from analysis.predictor import predict_trend
            with st.spinner(f"Loading {symbol}..."):
                df    = get_historical_data(yf_symbol, period=period)
                fund  = get_fundamental_data(yf_symbol)
                strats = run_all_strategies(df) if not df.empty else {}
                cons   = get_consensus(strats) if strats else {}
                da     = deep_analysis(df) if not df.empty else {}
                pred   = predict_trend(df) if not df.empty else {}
                st.session_state["search_result"] = {
                    "symbol": symbol, "yf_symbol": yf_symbol,
                    "df": df, "fund": fund, "strats": strats,
                    "cons": cons, "da": da, "pred": pred,
                }
        except Exception as e:
            st.error(f"Analysis error: {e}")
            return

    res = st.session_state.get("search_result")
    if not res:
        return

    symbol    = res["symbol"]
    df        = res["df"]
    fund      = res["fund"]
    strats    = res["strats"]
    cons      = res["cons"]
    da        = res.get("da", {})
    pred      = res["pred"]

    if df.empty:
        st.error(f"No data found for {symbol}. Check the symbol and try again.")
        return

    cmp = round(df["Close"].iloc[-1], 2)

    # ── Header ─────────────────────────────────────────────────────────────────
    name   = fund.get("name", symbol)
    sector = fund.get("sector", "—")
    h52    = fund.get("52w_high") or round(df["High"].tail(252).max(), 2)
    l52    = fund.get("52w_low")  or round(df["Low"].tail(252).min(), 2)
    mcap   = fund.get("market_cap")
    mcap_s = f"₹{mcap/1e7:,.0f} Cr" if mcap else "—"
    from_h = (cmp/h52 - 1)*100 if h52 else 0

    st.markdown(f"""
    <div style="margin-bottom:20px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:24px;font-weight:600;
                  color:#E8EDF5;line-height:1">{symbol}</div>
      <div style="font-size:13px;color:#2A3D58;margin-top:4px">{name} &nbsp;·&nbsp; {sector}</div>
    </div>""", unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, lbl, val, extra in [
        (c1, "CMP",         f"₹{cmp:,.2f}",    ""),
        (c2, "52W High",    f"₹{h52:,.2f}",    ""),
        (c3, "52W Low",     f"₹{l52:,.2f}",    ""),
        (c4, "Market Cap",  mcap_s,             ""),
        (c5, "From 52W H",  f"{from_h:+.1f}%", "neg" if from_h < -10 else "pos"),
    ]:
        color = "#FF4455" if extra == "neg" else "#00C87A" if extra == "pos" else "#E8EDF5"
        with col:
            st.markdown(f"""
            <div class="tt-metric">
              <div class="tt-metric-label">{lbl}</div>
              <div class="tt-metric-value" style="font-size:16px;color:{color}">{val}</div>
            </div>""", unsafe_allow_html=True)

    # ── Tabs: Chart / Fundamental / Technicals / Prediction ───────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Chart",  "📊 Fundamentals",
        "⚙ Technicals", "🔮 Prediction"
    ])

    with tab1:
        df_plot = df.tail(252)
        ema50  = df_plot["Close"].ewm(span=50).mean()
        ema200 = df_plot["Close"].ewm(span=200).mean()

        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_plot.index,
            open=df_plot["Open"], high=df_plot["High"],
            low=df_plot["Low"],   close=df_plot["Close"],
            name="Price",
            increasing=dict(line=dict(color="#00C87A"), fillcolor="#00281A"),
            decreasing=dict(line=dict(color="#FF4455"), fillcolor="#280A0A"),
        ))
        fig.add_trace(go.Scatter(x=df_plot.index, y=ema50,
                                  line=dict(color="#FFAA00", width=1.2), name="EMA 50"))
        fig.add_trace(go.Scatter(x=df_plot.index, y=ema200,
                                  line=dict(color="#00D4FF", width=1.2), name="EMA 200"))

        # Volume sub-chart
        vol_colors = ["#00281A" if c >= o else "#280A0A"
                      for c, o in zip(df_plot["Close"], df_plot["Open"])]
        fig.add_trace(go.Bar(
            x=df_plot.index, y=df_plot["Volume"],
            marker_color=vol_colors, opacity=0.4, name="Volume",
            yaxis="y2"
        ))
        fig = plotly_dark_layout(fig, height=420)
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            yaxis2=dict(overlaying="y", side="right", showgrid=False,
                        tickfont=dict(size=9, color="#2A3D58"), showticklabels=False),
            legend=dict(orientation="h", y=1.02, x=0, font=dict(size=10, color="#3A5070"))
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        page_section("Key Metrics")
        metrics = {
            "P/E Ratio":     fund.get("pe_ratio"),
            "P/B Ratio":     fund.get("pb_ratio"),
            "ROE":           f"{fund['roe']*100:.1f}%" if fund.get("roe") else "—",
            "Debt/Equity":   fund.get("debt_equity"),
            "Rev. Growth":   f"{fund['revenue_growth']*100:.1f}%" if fund.get("revenue_growth") else "—",
            "EPS (TTM)":     f"₹{fund['eps']:.2f}" if fund.get("eps") else "—",
            "Div. Yield":    f"{fund['dividend_yield']*100:.2f}%" if fund.get("dividend_yield") else "—",
            "Industry":      fund.get("industry", "—"),
        }
        cols = st.columns(4)
        for i, (k, v) in enumerate(metrics.items()):
            with cols[i % 4]:
                st.metric(k, str(v) if v is not None else "—")

        pe = fund.get("pe_ratio")
        if pe:
            band = "Undervalued" if pe < 15 else "Fair Value" if pe < 25 else "Premium"
            bc   = "#00C87A" if pe < 15 else "#FFAA00" if pe < 25 else "#FF4455"
            st.markdown(f"""
            <div style="background:#0A0F1C;border:1px solid #141D2E;border-left:2px solid {bc};
                        border-radius:8px;padding:14px 18px;margin-top:16px">
              <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#3A5070;
                           text-transform:uppercase;letter-spacing:0.1em">Valuation Assessment</span>
              <span style="font-family:'IBM Plex Mono',monospace;font-size:14px;font-weight:500;
                           color:{bc};margin-left:12px">{band}</span>
              <span style="color:#2A3D58;font-size:12px;margin-left:8px">(P/E: {pe:.1f}x)</span>
            </div>""", unsafe_allow_html=True)

    with tab3:
        # Consensus
        cs = cons.get("signal", "HOLD")
        cc = {"BUY":"#00C87A","SELL":"#FF4455","HOLD":"#FFAA00"}.get(cs,"#4A6080")
        agreeing  = cons.get("agreeing_strategies", 0)
        n_strats  = len(strats)
        conf_pct  = cons.get("confidence", 0) * 100
        warn      = cons.get("warning", "")
        reason_s  = cons.get("reason_summary", "")

        st.markdown(f"""
        <div style="background:#0A0F1C;border:1px solid #141D2E;border-radius:12px;
                    padding:20px 24px;margin-bottom:16px">
          <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px">
            <div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#2A3D58;
                          text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px">
                Consensus Signal
              </div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:28px;font-weight:700;
                          color:{cc}">{cs}</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070;margin-top:6px">
                {cons.get('buy_votes',0)} BUY &nbsp;·&nbsp; {cons.get('sell_votes',0)} SELL
                &nbsp;·&nbsp; {cons.get('hold_votes',0)} HOLD &nbsp;·&nbsp;
                Confidence: {conf_pct:.0f}%
                {f'&nbsp;·&nbsp; {agreeing}/{n_strats} strategies agree' if agreeing > 0 else ''}
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#2A3D58;
                          margin-bottom:4px">Deep Analysis</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#4A6080">
                Trend: {da.get('short_trend','?')}/{da.get('mid_trend','?')}/{da.get('long_trend','?')}
                {'&nbsp;✓ Aligned' if da.get('trend_aligned') else ''}
              </div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#4A6080">
                14D ROC: {da.get('momentum_roc14', 0):+.1f}%
                &nbsp;·&nbsp; Vol: {da.get('annualised_vol', 0):.0f}%
              </div>
            </div>
          </div>
          {f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#3A5070;margin-top:10px;padding-top:8px;border-top:1px solid #0D1525">{reason_s}</div>' if reason_s else ''}
          {f'<div style="font-family:IBM Plex Mono,monospace;font-size:11px;color:#FFAA00;margin-top:6px">⚠ {warn}</div>' if warn else ''}
        </div>""", unsafe_allow_html=True)

        rows = []
        for s_name, s_res in strats.items():
            sig   = signal_badge(s_res["signal"])
            score = confidence_bar(s_res["score"])
            rows.append([
                f'<span style="color:#8AA0BE;font-family:\'IBM Plex Mono\',monospace;font-size:12px">{s_name}</span>',
                sig, score,
                f'<span style="color:#2A3D58;font-size:11px">{s_res["reason"][:65]}</span>',
            ])
        st.markdown(data_table(["Strategy","Signal","Score","Reason"], rows), unsafe_allow_html=True)

    with tab4:
        if not pred:
            st.info("Prediction unavailable — insufficient data.")
        else:
            d  = pred.get("direction","—")
            dc = "#00C87A" if d == "UP" else "#FF4455" if d == "DOWN" else "#FFAA00"
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px">
              <div class="tt-metric">
                <div class="tt-metric-label">Direction (12 months)</div>
                <div class="tt-metric-value" style="color:{dc}">{d}</div>
                <div class="tt-metric-delta {'pos' if pred.get('change_pct_12m',0)>0 else 'neg'}">
                  {pred.get('change_pct_12m',0):+.1f}%
                </div>
              </div>
              <div class="tt-metric">
                <div class="tt-metric-label">Target 12M</div>
                <div class="tt-metric-value" style="color:{dc}">₹{pred.get('target_12m',0):,.0f}</div>
              </div>
              <div class="tt-metric">
                <div class="tt-metric-label">Target 24M</div>
                <div class="tt-metric-value" style="color:{dc}">₹{pred.get('target_24m',0):,.0f}</div>
                <div class="tt-metric-delta {'pos' if pred.get('change_pct_24m',0)>0 else 'neg'}">
                  {pred.get('change_pct_24m',0):+.1f}%
                </div>
              </div>
              <div class="tt-metric">
                <div class="tt-metric-label">Annual Est. Return</div>
                <div class="tt-metric-value">{pred.get('annual_return_estimate',0):.1f}%</div>
              </div>
            </div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#1A2D40;
                        padding:10px 0;border-top:1px solid #0D1525">
              ⚠ Statistical projection only. Not financial advice.
            </div>""", unsafe_allow_html=True)

            # Chart with projection
            last_idx   = df.index[-1]
            future_idx = pd.date_range(last_idx, periods=25, freq="ME")[1:]
            proj_y     = [cmp] + [pred.get("target_12m", cmp)] * 12 + [pred.get("target_24m", cmp)] * 12

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.tail(504).index, y=df.tail(504)["Close"],
                line=dict(color="#00D4FF", width=1.5), name="Historical"
            ))
            fig.add_trace(go.Scatter(
                x=[df.index[-1]] + list(future_idx),
                y=proj_y,
                line=dict(color=dc, width=1.5, dash="dot"), name="Projection",
                fill="tozeroy",
                fillcolor=f"{dc}08",
            ))
            fig = plotly_dark_layout(fig, "Price Projection", height=320)
            st.plotly_chart(fig, use_container_width=True)
