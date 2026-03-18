"""
alerts/emailer.py — All alert emails sent via Resend API.
No SMTP, no Gmail setup — just a Resend API key.
"""
import os
import random
import string
import logging
import requests

logger = logging.getLogger(__name__)


def _cfg(section: str, key: str, fallback: str = "") -> str:
    """Read from st.secrets or environment variables."""
    try:
        import streamlit as st
        return st.secrets[section][key]
    except Exception:
        return os.getenv(f"{section.upper()}_{key.upper()}", fallback)


# ── Sender identity pools (same as auth.py) ───────────────────────────────────
_ALERT_SENDER_NAMES = [
    "Signal Monitor", "Alpha Dispatch", "Quant Alerts",
    "Market Watcher", "Trade Notify",   "Portfolio Pulse",
    "NSE Signal",     "Equity Monitor", "Risk Notify",
]
_ALERT_PREFIXES = [
    "signals", "alerts", "notify", "dispatch", "monitor",
    "trading", "market", "equity", "ops",
]


def _random_from(domain: str) -> str:
    """Build a randomised From address."""
    name   = random.choice(_ALERT_SENDER_NAMES)
    prefix = random.choice(_ALERT_PREFIXES)
    suffix = "".join(random.choices(string.digits, k=4))
    if domain:
        email = f"{prefix}-{suffix}@{domain}"
    else:
        email = "onboarding@resend.dev"
        name  = "Trading Terminal"
    return f"{name} <{email}>"


def _parse_recipients(raw: str) -> list:
    """Parse comma-separated email list, deduplicated."""
    parts = [e.strip() for e in raw.split(",") if e.strip()]
    seen, unique = set(), []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    return unique


def _send(subject: str, html: str, to: str = None) -> bool:
    """Send an email through the Resend API to all configured recipients."""
    api_key = _cfg("resend", "API_KEY", "")
    domain  = _cfg("resend", "FROM_DOMAIN", "").strip()

    # Resolve recipient list
    raw_to = to or (
        _cfg("email", "OTP_RECIPIENTS", "") or
        _cfg("email", "OTP_RECIPIENT",  "jayankgajjala@gmail.com")
    )
    recipients = _parse_recipients(raw_to)

    if not api_key:
        logger.warning("[emailer] No Resend API key — email skipped.")
        return False

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "from":    _random_from(domain),
                "to":      recipients,          # ← full list, one API call
                "subject": subject,
                "html":    html,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info(f"Email sent to {len(recipients)} recipient(s): {subject}")
            return True
        logger.error(f"Resend {resp.status_code}: {resp.text}")
        return False
    except Exception as e:
        logger.error(f"Resend request failed: {e}")
        return False


def _signal_color(signal: str) -> str:
    return {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#f59e0b"}.get(signal, "#888")


def _signal_emoji(signal: str) -> str:
    return {"BUY": "📈 BUY", "SELL": "📉 SELL", "HOLD": "⏸ HOLD"}.get(signal, signal)


def send_alert_email(signals: list[dict]) -> bool:
    """Send strategy alert email for a list of signal dicts."""
    if not signals:
        return False

    rows = ""
    for s in signals:
        color = _signal_color(s["signal"])
        rows += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b;font-weight:600">{s['symbol']}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b">
            <span style="background:{color};color:#fff;padding:3px 10px;border-radius:4px;
                         font-weight:700;font-size:13px">{s['signal']}</span>
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b">
            ₹{s.get('price', 0):,.2f}
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b;color:#94a3b8;font-size:13px">
            {s.get('best_strategy', '')}
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b;color:#94a3b8;font-size:12px">
            {s.get('reason', '')[:80]}
          </td>
          <td style="padding:10px 16px;border-bottom:1px solid #1e293b;color:#64748b;font-size:12px">
            {s.get('timestamp', '')}
          </td>
        </tr>
        """

    count = len(signals)
    buy_count = sum(1 for s in signals if s["signal"] == "BUY")
    sell_count = sum(1 for s in signals if s["signal"] == "SELL")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;margin:0;padding:24px">
      <div style="max-width:900px;margin:auto">
        <h2 style="color:#38bdf8;margin-bottom:4px">📊 Trading Terminal — Strategy Alerts</h2>
        <p style="color:#64748b;font-size:13px;margin-bottom:24px">
          {count} signal(s) generated &nbsp;|&nbsp;
          <span style="color:#22c55e">▲ {buy_count} BUY</span> &nbsp;
          <span style="color:#ef4444">▼ {sell_count} SELL</span>
        </p>
        <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden">
          <thead>
            <tr style="background:#0f172a;color:#94a3b8;font-size:12px;text-transform:uppercase">
              <th style="padding:10px 16px;text-align:left">Symbol</th>
              <th style="padding:10px 16px;text-align:left">Signal</th>
              <th style="padding:10px 16px;text-align:left">Price</th>
              <th style="padding:10px 16px;text-align:left">Strategy</th>
              <th style="padding:10px 16px;text-align:left">Reason</th>
              <th style="padding:10px 16px;text-align:left">Time</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p style="color:#334155;font-size:12px;margin-top:24px">
          This is an automated alert from your private trading terminal. Not financial advice.
        </p>
      </div>
    </body></html>
    """
    subject = f"[Trading Terminal] {buy_count} BUY · {sell_count} SELL alerts"
    return _send(subject, html)


def send_news_digest(articles: list[dict]) -> bool:
    """Send top news as an email digest."""
    if not articles:
        return False
    items = ""
    for a in articles[:15]:
        items += f"""
        <div style="border-bottom:1px solid #1e293b;padding:12px 0">
          <a href="{a.get('url','#')}" style="color:#38bdf8;font-size:14px;
             font-weight:600;text-decoration:none">{a.get('title','')}</a>
          <p style="color:#94a3b8;font-size:12px;margin:4px 0 0">
            {a.get('source','')} · {a.get('publishedAt','')[:10]}
          </p>
        </div>
        """
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px">
      <div style="max-width:700px;margin:auto">
        <h2 style="color:#38bdf8">📰 Market News Digest</h2>
        {items}
      </div>
    </body></html>
    """
    return _send("[Trading Terminal] Market News Digest", html)


def send_opportunity_alert(opportunities: list[dict]) -> bool:
    """Send new opportunities found from Nifty 500 scan."""
    if not opportunities:
        return False
    rows = "".join([
        f"<li style='margin:8px 0'><b style='color:#38bdf8'>{o['symbol']}</b> — "
        f"<span style='color:{_signal_color(o['signal'])}'>{o['signal']}</span> "
        f"@ ₹{o.get('price',0):,.2f} ({o.get('reason','')})</li>"
        for o in opportunities
    ])
    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px">
      <div style="max-width:700px;margin:auto">
        <h2 style="color:#38bdf8">🔍 New Opportunities — Nifty 500 Scan</h2>
        <ul style="padding-left:20px">{rows}</ul>
      </div>
    </body></html>
    """
    return _send(f"[Trading Terminal] {len(opportunities)} New Opportunities Found", html)
