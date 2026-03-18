"""ui/news_page.py"""
import streamlit as st
from ui.components import page_section, empty_state


def render():
    try:
        from news.fetcher import fetch_all_news, fetch_nifty_changes
        from config.settings import NIFTY50
    except ImportError as e:
        st.error(f"Import error: {e}")
        return

    # ── Filter bar ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        news_tab = st.selectbox(
            "Category",
            ["Portfolio", "Nifty 50", "Global Macro"],
            key="news_cat"
        )
    with col2:
        refresh = st.button("Refresh →", key="news_refresh")

    cache_key = f"news_{news_tab}"
    if refresh or cache_key not in st.session_state:
        with st.spinner("Fetching latest news..."):
            try:
                if news_tab == "Portfolio":
                    articles = fetch_all_news(NIFTY50[:10], include_global=False)
                elif news_tab == "Nifty 50":
                    articles = fetch_all_news(NIFTY50[:5], include_global=True)
                else:
                    articles = fetch_all_news(
                        ["RBI", "FII", "inflation", "GDP", "crude"],
                        include_global=True
                    )
                st.session_state[cache_key] = articles
            except Exception as e:
                st.error(f"News fetch error: {e}")
                return

    articles = st.session_state.get(cache_key, [])

    if not articles:
        empty_state("No articles found", "Check your NEWS_API_KEY in secrets")
        return

    # ── Stats strip ────────────────────────────────────────────────────────────
    page_section(f"{len(articles)} Articles  ·  {news_tab}")

    # ── Article cards ──────────────────────────────────────────────────────────
    for a in articles[:30]:
        source = a.get("source", {})
        src_name = source if isinstance(source, str) else source.get("name", "")
        pub = a.get("publishedAt", "")[:10]
        title = a.get("title", "No title")
        url   = a.get("url", "#")
        desc  = (a.get("description") or "")[:200]

        # Colour-code by source type
        if any(k in src_name.lower() for k in ["economic", "times", "mint", "hindu"]):
            accent = "#00D4FF"
        elif any(k in src_name.lower() for k in ["reuters", "bloomberg", "cnbc"]):
            accent = "#00C87A"
        else:
            accent = "#2A3D58"

        st.markdown(f"""
        <div class="tt-news-card" style="border-left:2px solid {accent}22">
          <a class="tt-news-title" href="{url}" target="_blank">{title}</a>
          <div class="tt-news-meta">
            <span style="color:{accent}">{src_name}</span>
            &nbsp;·&nbsp; {pub}
          </div>
          {'<div style="color:#2A3D58;font-size:12px;margin-top:6px;line-height:1.5">' + desc + '...</div>' if desc else ''}
        </div>""", unsafe_allow_html=True)

    # ── Nifty changes sidebar ──────────────────────────────────────────────────
    if news_tab == "Nifty 50":
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        page_section("Index Reconstitution Alerts")
        try:
            changes = fetch_nifty_changes()
            if changes:
                for a in changes[:5]:
                    st.markdown(f"""
                    <div style="padding:8px 0;border-bottom:1px solid #0D1525">
                      <a href="{a.get('url','#')}" target="_blank"
                         style="color:#3A5070;font-size:12px;text-decoration:none">
                        {a.get('title','')[:90]}
                      </a>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#1A2D40;font-size:12px;padding:12px">No recent announcements.</div>',
                            unsafe_allow_html=True)
        except Exception:
            pass
