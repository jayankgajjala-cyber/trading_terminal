"""ui/news_page.py — AI News Intelligence dashboard."""
import streamlit as st
from ui.components import page_section, empty_state, data_table

SENT_COLOR = {"BULLISH": "#00C87A", "BEARISH": "#FF4455", "NEUTRAL": "#FFAA00"}
IMPACT_COLOR = {"POSITIVE": "#00C87A", "NEGATIVE": "#FF4455", "NEUTRAL": "#4A6080"}
REC_COLOR = {"BUY": "#00C87A", "SELL": "#FF4455", "HOLD": "#FFAA00"}


def _sentiment_badge(label: str) -> str:
    c = SENT_COLOR.get(label, "#4A6080")
    return (f'<span style="background:{c}22;color:{c};border:1px solid {c}44;'
            f'padding:2px 9px;border-radius:4px;font-family:\'IBM Plex Mono\',monospace;'
            f'font-size:11px;font-weight:600">{label}</span>')


def _rec_badge(rec: str) -> str:
    c = REC_COLOR.get(rec, "#4A6080")
    return (f'<span style="background:{c}22;color:{c};border:1px solid {c}44;'
            f'padding:3px 11px;border-radius:4px;font-family:\'IBM Plex Mono\',monospace;'
            f'font-size:12px;font-weight:700">{rec}</span>')


def _conf_bar(pct: float) -> str:
    color = "#00C87A" if pct >= 70 else "#FFAA00" if pct >= 45 else "#FF4455"
    return (f'<div style="display:inline-flex;align-items:center;gap:6px">'
            f'<div style="background:#141D2E;border-radius:3px;height:5px;width:60px;overflow:hidden">'
            f'<div style="background:{color};height:100%;width:{min(pct,100):.0f}%;border-radius:3px"></div></div>'
            f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#3A5070">'
            f'{pct:.0f}%</span></div>')


def render():
    try:
        from config.settings import NIFTY50
        from news.fetcher import fetch_all_news, fetch_nifty_changes
        from news.ai_analyst import get_stock_news_insight, get_portfolio_insights
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    # ── Mode selector ──────────────────────────────────────────────────────────
    col_mode, col_refresh, col_claude = st.columns([2, 1, 1])
    with col_mode:
        mode = st.selectbox(
            "Mode",
            ["Portfolio AI Insights", "Market News Feed", "Nifty 50 Updates"],
            key="news_mode"
        )
    with col_refresh:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        refresh = st.button("Refresh →", key="news_refresh")
    with col_claude:
        use_claude = st.checkbox("Use AI (Claude)", value=True, key="use_claude_news",
                                 help="Uses Claude API for deeper summaries (optional)")

    # ══════════════════════════════════════════════════════════════════════════
    # Mode 1: Portfolio AI Insights
    # ══════════════════════════════════════════════════════════════════════════
    if mode == "Portfolio AI Insights":
        page_section("AI News Insights per Stock")

        # Load portfolio symbols
        try:
            from data.portfolio import load_csv
            df_port, _ = load_csv()
            if df_port is not None and not df_port.empty:
                symbols = df_port["symbol"].dropna().tolist()
            else:
                symbols = NIFTY50[:10]
        except Exception:
            symbols = NIFTY50[:10]

        # Symbol picker
        sym_clean = [s.replace(".NS", "") for s in symbols[:20]]
        selected  = st.multiselect(
            "Stocks to analyse",
            options=sym_clean,
            default=sym_clean[:5],
            key="news_syms"
        )
        selected_full = [s + ".NS" if ".NS" not in s else s for s in selected]

        run_btn = st.button("Analyse News →", type="primary", key="run_news_ai")

        cache_key = f"news_ai_{'_'.join(selected[:5])}"
        if run_btn or (cache_key not in st.session_state and not refresh):
            if selected_full:
                # Optionally load existing tech signals
                tech_sigs = {}
                if "last_signals" in st.session_state:
                    for sig in st.session_state["last_signals"]:
                        tech_sigs[sig["symbol"]] = sig

                with st.spinner(f"Analysing news for {len(selected_full)} stocks..."):
                    try:
                        insights = get_portfolio_insights(
                            selected_full,
                            tech_signals=tech_sigs if tech_sigs else None,
                            use_claude=use_claude,
                        )
                        st.session_state[cache_key] = insights
                    except Exception as e:
                        st.error(f"News analysis failed: {e}")
                        return

        insights = st.session_state.get(cache_key, {})
        if not insights:
            empty_state("No insights yet", "Select stocks and click 'Analyse News'")
            return

        # ── Summary table ──────────────────────────────────────────────────────
        page_section("News Intelligence Summary")
        rows = []
        for sym, ins in insights.items():
            sym_label = sym.replace(".NS", "")
            sent  = _sentiment_badge(ins.get("sentiment", "NEUTRAL"))
            rec   = _rec_badge(ins.get("combined_recommendation", "HOLD"))
            conf  = _conf_bar(ins.get("combined_confidence", 50))
            conflict = ins.get("conflict", {})
            warn  = ('⚠ CONFLICT' if conflict.get("has_conflict") else
                     '✓ Aligned'  if ins.get("combined_recommendation") != "HOLD" else "—")
            warn_c = "#FFAA00" if conflict.get("has_conflict") else "#00C87A" if warn == '✓ Aligned' else "#3A5070"
            rows.append([
                f'<code style="color:#E8EDF5;font-size:13px">{sym_label}</code>',
                sent, rec, conf,
                f'<span style="color:{warn_c};font-family:\'IBM Plex Mono\',monospace;font-size:11px">{warn}</span>',
                f'<span style="color:#2A3D58;font-size:11px">{ins.get("takeaway","")[:60]}</span>',
            ])
        st.markdown(
            data_table(["Stock","Sentiment","Rec","Confidence","Signal","Key Takeaway"], rows),
            unsafe_allow_html=True
        )

        # ── Detailed cards ─────────────────────────────────────────────────────
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        page_section("Detailed Analysis Cards")

        for sym, ins in insights.items():
            sym_label  = sym.replace(".NS","")
            sent_c     = SENT_COLOR.get(ins.get("sentiment","NEUTRAL"), "#4A6080")
            rec_val    = ins.get("combined_recommendation","HOLD")
            rec_c      = REC_COLOR.get(rec_val, "#4A6080")
            conf_val   = ins.get("combined_confidence", 50)
            conflict   = ins.get("conflict", {})
            events_str = ", ".join(ins.get("events",[])[:4]) or "general"
            ai_tag     = ' <span style="color:#00D4FF;font-size:9px">✦ AI</span>' \
                         if ins.get("ai_enhanced") else ""

            # Conflict banner
            conflict_html = ""
            if conflict.get("has_conflict"):
                conflict_html = f"""
                <div style="background:#1A0A00;border:1px solid #FFAA0044;border-radius:6px;
                             padding:8px 12px;margin:8px 0;font-family:'IBM Plex Mono',monospace;
                             font-size:11px;color:#FFAA00">
                  ⚠ CONFLICT DETECTED: {conflict.get('explanation','')}
                </div>"""
            elif conflict.get("action","").startswith("CONFIRMED"):
                conflict_html = f"""
                <div style="background:#0A2210;border:1px solid #00C87A44;border-radius:6px;
                             padding:8px 12px;margin:8px 0;font-family:'IBM Plex Mono',monospace;
                             font-size:11px;color:#00C87A">
                  ✓ {conflict.get('action','')}
                </div>"""

            st.markdown(f"""
            <div style="background:#0A0F1C;border:1px solid #141D2E;border-left:3px solid {sent_c};
                        border-radius:10px;padding:18px 20px;margin-bottom:12px">

              <!-- Header row -->
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <div style="display:flex;align-items:center;gap:12px">
                  <code style="color:#E8EDF5;font-size:16px;font-weight:600">{sym_label}</code>
                  {_sentiment_badge(ins.get("sentiment","NEUTRAL"))}{ai_tag}
                </div>
                <div style="display:flex;align-items:center;gap:10px">
                  {_rec_badge(rec_val)}
                  {_conf_bar(conf_val)}
                </div>
              </div>

              <!-- Summary -->
              <div style="color:#8AA0BE;font-size:13px;line-height:1.6;margin-bottom:10px">
                {ins.get("summary","—")}
              </div>

              <!-- Event tags -->
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px">
                {''.join(f'<span style="background:#080D18;color:#3A5070;border:1px solid #1A2540;padding:2px 8px;border-radius:4px;font-family:IBM Plex Mono,monospace;font-size:10px">{e}</span>' for e in ins.get("events",[])[:5])}
              </div>

              {conflict_html}

              <!-- Impact + risk row -->
              <div style="display:flex;gap:20px;font-family:'IBM Plex Mono',monospace;font-size:11px;
                          color:#2A3D58;flex-wrap:wrap;margin-bottom:8px">
                <span>Short: <span style="color:{IMPACT_COLOR.get(ins.get('short_impact','NEUTRAL'),'#4A6080')}">{ins.get('short_impact','—')}</span></span>
                <span>Long: <span style="color:{IMPACT_COLOR.get(ins.get('long_impact','NEUTRAL'),'#4A6080')}">{ins.get('long_impact','—')}</span></span>
                <span>Risk: <span style="color:#FFAA00">{ins.get('risk','—')[:60]}</span></span>
              </div>

              <!-- Reasoning -->
              <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#1E3050;
                          padding-top:8px;border-top:1px solid #0D1525">
                Reason: {ins.get('combined_reason','')[:100]}
                · Sources: {ins.get('articles_used',0)} articles
              </div>
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Mode 2: Raw Market News Feed
    # ══════════════════════════════════════════════════════════════════════════
    elif mode == "Market News Feed":
        cat_col, _ = st.columns([2, 3])
        with cat_col:
            cat = st.selectbox("Category", ["Portfolio", "Nifty 50", "Global Macro"], key="news_cat2")

        cache_key = f"news_raw_{cat}"
        if refresh or cache_key not in st.session_state:
            with st.spinner("Fetching news..."):
                try:
                    if cat == "Portfolio":
                        articles = fetch_all_news(NIFTY50[:10], include_global=False)
                    elif cat == "Nifty 50":
                        articles = fetch_all_news(NIFTY50[:5], include_global=True)
                    else:
                        articles = fetch_all_news(
                            ["RBI","FII","inflation","GDP","crude"], include_global=True)
                    st.session_state[cache_key] = articles
                except Exception as e:
                    st.error(f"News fetch error: {e}")
                    return

        articles = st.session_state.get(cache_key, [])
        if not articles:
            empty_state("No articles found", "Check your NEWS_API_KEY in secrets")
            return

        page_section(f"{len(articles)} Articles · {cat}")
        for a in articles[:30]:
            src  = a.get("source", {})
            src_name = src if isinstance(src, str) else src.get("name","")
            pub  = a.get("publishedAt","")[:10]
            desc = (a.get("description") or "")[:200]
            accent = ("#00D4FF" if any(k in src_name.lower() for k in ["economic","times","mint"])
                      else "#00C87A" if any(k in src_name.lower() for k in ["reuters","bloomberg"])
                      else "#2A3D58")
            st.markdown(f"""
            <div class="tt-news-card" style="border-left:2px solid {accent}33">
              <a class="tt-news-title" href="{a.get('url','#')}" target="_blank">{a.get('title','')}</a>
              <div class="tt-news-meta">
                <span style="color:{accent}">{src_name}</span> &nbsp;·&nbsp; {pub}
              </div>
              {'<div style="color:#2A3D58;font-size:12px;margin-top:6px">' + desc + '...</div>' if desc else ''}
            </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # Mode 3: Nifty 50 Updates
    # ══════════════════════════════════════════════════════════════════════════
    elif mode == "Nifty 50 Updates":
        page_section("Nifty 50 Index Updates")
        if refresh or "nifty_changes" not in st.session_state:
            with st.spinner("Fetching index news..."):
                try:
                    st.session_state["nifty_changes"] = fetch_nifty_changes()
                except Exception as e:
                    st.error(str(e))
        changes = st.session_state.get("nifty_changes", [])
        if not changes:
            empty_state("No index announcements found")
        for a in changes[:10]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid #0D1525">
              <a href="{a.get('url','#')}" target="_blank"
                 style="color:#8AA0BE;font-size:13px;font-weight:500;text-decoration:none">
                {a.get('title','')[:100]}
              </a>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#1E3050;margin-top:3px">
                {a.get('publishedAt','')[:10]}
              </div>
            </div>""", unsafe_allow_html=True)
