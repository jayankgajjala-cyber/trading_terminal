"""ui/alerts_page.py"""
import streamlit as st
from ui.components import page_section


def render():
    page_section("Email Alert Settings")

    try:
        from config.settings import OTP_RECIPIENT_EMAIL, RESEND_API_KEY, RESEND_DOMAIN
        email_ok = bool(RESEND_API_KEY)
        sender_domain = RESEND_DOMAIN or "resend.dev (shared)"
    except Exception:
        email_ok = False
        OTP_RECIPIENT_EMAIL = "—"
        sender_domain = "—"

    # ── Status ─────────────────────────────────────────────────────────────────
    status_color = "#00C87A" if email_ok else "#FF4455"
    status_text  = "CONFIGURED" if email_ok else "NOT CONFIGURED"

    st.markdown(f"""
    <div style="background:{'#0A2218' if email_ok else '#1A0A0A'};
                border:1px solid {status_color}33;border-radius:10px;
                padding:18px 22px;margin-bottom:20px">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:{status_color};
                  letter-spacing:0.08em">{'●' if email_ok else '✗'} RESEND {status_text}</div>
      <div style="font-size:12px;color:#2A3D58;margin-top:6px">
        Recipient: <code style="color:#4A6080">{OTP_RECIPIENT_EMAIL}</code>
        &nbsp;·&nbsp;
        Sender domain: <code style="color:#4A6080">{sender_domain}</code>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Test alert ─────────────────────────────────────────────────────────────
    page_section("Send Test Alert")

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Send Test Email →", type="primary", key="send_test_email"):
            try:
                from alerts.emailer import send_alert_email
                test_signal = [{
                    "symbol": "TEST.NS", "signal": "BUY", "price": 1234.56,
                    "best_strategy": "EMA Crossover",
                    "reason": "Test alert from Trading Terminal",
                    "confidence": 0.85, "timestamp": "12:00:00 IST"
                }]
                ok = send_alert_email(test_signal)
                if ok:
                    st.success(f"Test email sent to {OTP_RECIPIENT_EMAIL}")
                else:
                    st.error("Email send failed. Check GMAIL credentials in secrets.")
            except Exception as e:
                st.error(f"Error: {e}")

    # ── Scheduler status ────────────────────────────────────────────────────────
    page_section("Scheduler Jobs")

    jobs = [
        ("Signal Check",    "Every 5 min · Mon–Fri 9:15–15:30 IST",  "Portfolio watchlist"),
        ("Weekly Analysis", "Monday 7:00 AM IST",                    "Full Nifty 50 backtest"),
        ("Nifty 500 Scan",  "Friday 4:00 PM IST",                    "Opportunity detection"),
        ("News Digest",     "Daily 8:00 AM IST · Mon–Fri",           "Email news summary"),
    ]

    rows_html = ""
    for name, schedule, desc in jobs:
        rows_html += f"""
        <tr style="border-bottom:1px solid #0D1525">
          <td style="padding:11px 14px;color:#C8D6E5;font-family:'IBM Plex Mono',monospace;font-size:12px">{name}</td>
          <td style="padding:11px 14px;color:#00D4FF;font-family:'IBM Plex Mono',monospace;font-size:11px">{schedule}</td>
          <td style="padding:11px 14px;color:#3A5070;font-size:12px">{desc}</td>
          <td style="padding:11px 14px">
            <span style="background:#0A2218;color:#00C87A;border:1px solid #00C87A33;
                         padding:2px 10px;border-radius:4px;font-family:'IBM Plex Mono',monospace;
                         font-size:10px;letter-spacing:0.05em">ACTIVE</span>
          </td>
        </tr>"""

    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;background:#0A0F1C;border-radius:10px;
                  overflow:hidden;border:1px solid #141D2E">
      <thead><tr style="background:#080D18;border-bottom:1px solid #141D2E">
        <th style="padding:10px 14px;text-align:left;font-family:'IBM Plex Mono',monospace;
                   font-size:10px;color:#2A3D58;text-transform:uppercase;letter-spacing:0.08em">Job</th>
        <th style="padding:10px 14px;text-align:left;font-family:'IBM Plex Mono',monospace;
                   font-size:10px;color:#2A3D58;text-transform:uppercase;letter-spacing:0.08em">Schedule</th>
        <th style="padding:10px 14px;text-align:left;font-family:'IBM Plex Mono',monospace;
                   font-size:10px;color:#2A3D58;text-transform:uppercase;letter-spacing:0.08em">Description</th>
        <th style="padding:10px 14px;text-align:left;font-family:'IBM Plex Mono',monospace;
                   font-size:10px;color:#2A3D58;text-transform:uppercase;letter-spacing:0.08em">Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#1A2D40;
                padding:12px 0;margin-top:8px">
      Note: On Streamlit Cloud, run scheduler_runner.py separately on a local machine or server.
      Streamlit Cloud does not support background processes.
    </div>""", unsafe_allow_html=True)

    # ── Secrets config guide ────────────────────────────────────────────────────
    page_section("Secrets Configuration")

    st.markdown("""
    <div style="background:#060A12;border:1px solid #141D2E;border-radius:10px;
                padding:20px 22px;font-family:'IBM Plex Mono',monospace;font-size:12px;
                color:#3A5070;line-height:2">
      Add these to Streamlit Cloud → App Settings → Secrets:<br><br>
      <code style="color:#E8EDF5;background:#0A0F1C;padding:16px;display:block;
                    border-radius:8px;border:1px solid #1A2540;white-space:pre;font-size:11px">
[auth]
USERNAME = "Jayank8294"
PASSWORD_HASH = "bcrypt_hash_here"

[email]
OTP_RECIPIENT = "jayankgajjala@gmail.com"

[resend]
API_KEY = "re_xxxxxxxxxxxxxxxxxxxx"
FROM_DOMAIN = "yourdomain.com"   # or leave blank for resend.dev

[zerodha]
API_KEY = "your_kite_api_key"
API_SECRET = "your_kite_secret"

[apis]
ALPHA_VANTAGE_KEY = "your_av_key"
NEWS_API_KEY = "your_newsapi_key"
      </code>
    </div>""", unsafe_allow_html=True)
