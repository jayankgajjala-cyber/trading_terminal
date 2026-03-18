"""
ui/components.py — Reusable styled components for the dark terminal UI.
"""
import streamlit as st


def metric_card(label: str, value: str, delta: str = "", delta_type: str = "neu"):
    """Render a styled metric card."""
    delta_html = f'<div class="tt-metric-delta {delta_type}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="tt-metric">
      <div class="tt-metric-label">{label}</div>
      <div class="tt-metric-value">{value}</div>
      {delta_html}
    </div>""", unsafe_allow_html=True)


def panel(title: str, icon: str = ""):
    """Return a context manager for a titled panel card."""
    prefix = f"{icon} " if icon else ""
    st.markdown(f"""
    <div class="tt-panel">
      <div class="tt-panel-title">{prefix}{title}</div>
    """, unsafe_allow_html=True)


def close_panel():
    st.markdown("</div>", unsafe_allow_html=True)


def signal_badge(signal: str) -> str:
    cls = {"BUY": "sig-buy", "SELL": "sig-sell", "HOLD": "sig-hold"}.get(signal, "sig-hold")
    return f'<span class="{cls}">{signal}</span>'


def confidence_bar(score: float, color: str = "#00D4FF") -> str:
    pct = int(min(max(score, 0), 1) * 100)
    return f"""
    <span class="conf-bar-bg">
      <span class="conf-bar-fill" style="width:{pct}%;background:{color}"></span>
    </span>
    <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#2E4060;
                 margin-left:5px">{pct}%</span>"""


def page_section(title: str):
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin:24px 0 14px">
      <div style="width:3px;height:14px;background:#00D4FF;border-radius:2px;flex-shrink:0"></div>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:500;
                   color:#3A5070;text-transform:uppercase;letter-spacing:0.1em">{title}</span>
    </div>""", unsafe_allow_html=True)


def empty_state(message: str, hint: str = ""):
    hint_html = f'<div style="color:#1A2D40;font-size:12px;margin-top:8px">{hint}</div>' if hint else ""
    st.markdown(f"""
    <div style="text-align:center;padding:48px 24px;background:#0A0F1C;
                border:1px dashed #141D2E;border-radius:12px">
      <div style="font-size:28px;margin-bottom:12px;opacity:0.3">◈</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;color:#2A3D58">{message}</div>
      {hint_html}
    </div>""", unsafe_allow_html=True)


def plotly_dark_layout(fig, title: str = "", height: int = 360):
    """Apply consistent dark theme to any plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(family="IBM Plex Mono", size=13, color="#3A5070"),
                   x=0, xanchor="left") if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#080D18",
        font=dict(family="IBM Plex Mono", color="#4A6080", size=11),
        height=height,
        margin=dict(l=8, r=8, t=36 if title else 8, b=8),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#3A5070", size=11)),
        xaxis=dict(gridcolor="#0D1525", linecolor="#141D2E", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#0D1525", linecolor="#141D2E", tickfont=dict(size=10)),
    )
    return fig


def data_table(headers: list[str], rows: list[list]) -> str:
    """Build a styled HTML data table."""
    th_html = "".join(f"<th>{h}</th>" for h in headers)
    tr_html = ""
    for row in rows:
        tds = "".join(f"<td>{cell}</td>" for cell in row)
        tr_html += f"<tr>{tds}</tr>"
    return f"""
    <table class="tt-table">
      <thead><tr>{th_html}</tr></thead>
      <tbody>{tr_html}</tbody>
    </table>"""
