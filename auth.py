"""
auth.py — Login + OTP system with premium dark terminal UI.
OTP is sent via Resend API from a randomised sender address
to ALL configured recipients simultaneously.

Resend setup (free — 3,000 emails/month):
  1. Sign up at https://resend.com
  2. Create an API key at https://resend.com/api-keys
  3. Add to st.secrets:

       [resend]
       API_KEY = "re_xxxxxxxxxxxx"
       FROM_DOMAIN = "yourdomain.com"   # leave blank to use resend.dev

  Multiple recipients — use a comma-separated list:
       [email]
       OTP_RECIPIENTS = "you@gmail.com, backup@gmail.com, phone@txt.att.net"
"""
import random, string, time, os
import requests
import streamlit as st

OTP_EXPIRY = 300  # 5 minutes

# ── Sender identity pools ─────────────────────────────────────────────────────
_SENDER_NAMES = [
    "Market Sentinel", "Quant Relay",    "Signal Dispatch",
    "Alpha Notify",    "Trade Watcher",  "Portfolio Guard",
    "NSE Monitor",     "Index Relay",    "Equity Pulse",
    "Risk Beacon",
]
_SENDER_PREFIXES = [
    "noreply", "alerts", "notify", "dispatch", "ping",
    "signal",  "secure", "auth",   "verify",   "access",
    "system",  "ops",    "bot",    "svc",       "auto",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg(section: str, key: str, fallback: str = "") -> str:
    """Read from st.secrets first, then environment, then fallback."""
    try:
        return st.secrets[section][key]
    except Exception:
        return os.getenv(f"{section.upper()}_{key.upper()}", fallback)


def _parse_recipients(raw: str) -> list:
    """
    Parse one or more email addresses from a comma-separated string.
    Supports any of:
        "a@x.com"
        "a@x.com, b@y.com"
        "a@x.com,b@y.com,c@z.com"
    Returns a deduplicated, ordered list.
    """
    parts = [e.strip() for e in raw.split(",") if e.strip()]
    seen, unique = set(), []
    for p in parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    return unique


def _mask_email(email: str) -> str:
    """'jayank@gmail.com' → 'j*****k@gmail.com'"""
    try:
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked = local[0] + "*"
        else:
            masked = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked}@{domain}"
    except Exception:
        return email


def _random_sender(domain: str):
    """Return (display_name, from_email) with a fresh random identity."""
    name   = random.choice(_SENDER_NAMES)
    prefix = random.choice(_SENDER_PREFIXES)
    suffix = "".join(random.choices(string.digits, k=4))
    if domain:
        email = f"{prefix}-{suffix}@{domain}"
    else:
        email = "onboarding@resend.dev"
        name  = "Trading Terminal"
    return name, email


def verify_password(plain: str) -> bool:
    stored_hash = _cfg("auth", "PASSWORD_HASH", "")
    if not stored_hash:
        return plain == "Jayanju@9498"   # first-run plaintext fallback
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), stored_hash.encode())
    except Exception:
        return False


# ── Core OTP sender ────────────────────────────────────────────────────────────

def send_otp(otp: str) -> bool:
    """
    Send OTP via Resend API to ALL configured recipients in one API call.
    Resend's 'to' field is a list — all addresses receive the same email.
    Falls back to console print when no API key is set (local dev).
    """
    api_key = _cfg("resend", "API_KEY", "")
    domain  = _cfg("resend", "FROM_DOMAIN", "").strip()

    # Support both OTP_RECIPIENTS (new) and OTP_RECIPIENT (legacy single)
    raw = _cfg("email", "OTP_RECIPIENTS", "") or \
          _cfg("email", "OTP_RECIPIENT",  "jayankgajjala@gmail.com")
    recipients = _parse_recipients(raw)

    # ── Dev / demo mode ──────────────────────────────────────────────────────
    if not api_key:
        print(f"\n[DEV MODE — no Resend key]  OTP: {otp}  →  {recipients}\n")
        return True

    sender_name, sender_email = _random_sender(domain)

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#060A12;font-family:'Courier New',monospace">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#060A12;padding:48px 24px">
    <tr><td align="center">
      <table width="380" cellpadding="0" cellspacing="0"
             style="background:#0A0F1C;border:1px solid #141D2E;border-radius:14px;
                    overflow:hidden;max-width:380px">

        <tr><td height="2"
             style="background:linear-gradient(90deg,transparent,#00D4FF66,transparent)">
        </td></tr>

        <tr><td style="padding:28px 32px 0">
          <div style="font-size:11px;color:#00D4FF;letter-spacing:0.18em;
                      text-transform:uppercase;margin-bottom:6px">
            ◈ &nbsp;Trading Terminal
          </div>
          <div style="font-size:18px;font-weight:600;color:#E8EDF5;
                      letter-spacing:-0.01em">
            Secure Login OTP
          </div>
        </td></tr>

        <tr><td style="padding:18px 32px 0">
          <div style="height:1px;background:#141D2E"></div>
        </td></tr>

        <tr><td style="padding:24px 32px">
          <div style="font-size:11px;color:#2A3D58;letter-spacing:0.1em;
                      text-transform:uppercase;margin-bottom:14px">
            One-Time Password
          </div>
          <div style="background:#060A12;border:1px solid #1A2540;border-radius:10px;
                      padding:20px 24px;text-align:center">
            <span style="font-size:42px;font-weight:700;letter-spacing:14px;
                         color:#00D4FF;font-family:'Courier New',Courier,monospace">
              {otp}
            </span>
          </div>
        </td></tr>

        <tr><td style="padding:0 32px 28px">
          <div style="font-size:11px;color:#2A3D58;line-height:1.7">
            Valid for <span style="color:#4A6080">5 minutes</span>
            &nbsp;·&nbsp; Do not share this code
            &nbsp;·&nbsp; Sender: <span style="color:#3A5070">{sender_name}</span>
          </div>
        </td></tr>

        <tr><td style="padding:14px 32px;background:#080D18;border-top:1px solid #0D1525">
          <div style="font-size:10px;color:#1A2D40;letter-spacing:0.05em">
            If you did not request this, ignore this email.
            This is an automated message — do not reply.
          </div>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
            },
            json={
                "from":    f"{sender_name} <{sender_email}>",
                "to":      recipients,          # ← list of all recipients
                "subject": f"Your OTP: {otp}  —  Trading Terminal",
                "html":    html_body,
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        else:
            err = resp.json().get("message", resp.text)
            st.error(f"Resend error ({resp.status_code}): {err}")
            return False
    except Exception as e:
        st.error(f"Network error sending OTP: {e}")
        return False


# ── Login page UI ──────────────────────────────────────────────────────────────

def render_login_page():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&family=IBM+Plex+Sans:wght@300;400;500&display=swap');
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
        background: #060A12 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    #MainMenu, footer, header, [data-testid="stToolbar"],
    [data-testid="stDecoration"], [data-testid="stSidebar"],
    [data-testid="collapsedControl"] { display: none !important; }
    .main .block-container { padding: 0 !important; }

    body::before {
        content: '';
        position: fixed; inset: 0;
        background-image:
            linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        pointer-events: none;
        z-index: 0;
    }
    .login-wrap {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 40px 20px;
        position: relative;
        z-index: 1;
    }
    .login-card {
        width: 100%;
        max-width: 380px;
        background: #0A0F1C;
        border: 1px solid #141D2E;
        border-radius: 16px;
        padding: 40px 36px;
        position: relative;
        overflow: hidden;
    }
    .login-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, #00D4FF55, transparent);
    }
    .login-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    .login-logo-icon {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #00D4FF22, #0066FF22);
        border: 1px solid #00D4FF33;
        border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 18px;
    }
    .login-logo-name {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 14px;
        font-weight: 600;
        color: #E8EDF5;
        letter-spacing: 0.04em;
    }
    .login-tagline {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #2A3D58;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 32px;
    }
    .login-divider { height: 1px; background: #141D2E; margin: 24px 0; }
    .stTextInput > div > div > input {
        background: #060A12 !important;
        border: 1px solid #1A2540 !important;
        border-radius: 8px !important;
        color: #C8D6E5 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 14px !important;
        padding: 10px 14px !important;
        height: 42px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #00D4FF55 !important;
        box-shadow: 0 0 0 3px #00D4FF0D !important;
    }
    .stTextInput label {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        color: #2A3D58 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #003D66, #005588) !important;
        color: #00D4FF !important;
        border: 1px solid #00D4FF44 !important;
        border-radius: 8px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 12px !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        transition: all 0.2s !important;
        margin-top: 8px !important;
    }
    .stButton > button:hover {
        box-shadow: 0 0 24px #00D4FF22 !important;
        border-color: #00D4FF77 !important;
    }
    label, [data-testid="stFormLabel"] {
        color: #2A3D58 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
    }
    [data-testid="stAlert"] {
        background: #0A1020 !important;
        border: 1px solid #1A2540 !important;
        border-radius: 8px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 12px !important;
    }
    .stForm { background: transparent !important; border: none !important; }
    </style>

    <div class="login-wrap">
      <div class="login-card">
        <div class="login-logo">
          <div class="login-logo-icon">📈</div>
          <span class="login-logo-name">TRADE TERMINAL</span>
        </div>
        <div class="login-tagline">Private Portfolio Intelligence System</div>
        <div class="login-divider"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        if not st.session_state.get("otp_sent"):
            with st.form("login_form", clear_on_submit=False):
                username  = st.text_input("Username")
                password  = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Send OTP →")
                if submitted:
                    auth_user = _cfg("auth", "USERNAME", "Jayank8294")
                    if username == auth_user and verify_password(password):
                        otp = "".join(random.choices(string.digits, k=6))
                        if send_otp(otp):
                            st.session_state.update({
                                "otp_value":     otp,
                                "otp_timestamp": time.time(),
                                "otp_sent":      True,
                            })
                            st.rerun()
                        else:
                            st.error("Could not send OTP. Check Resend config in secrets.")
                    else:
                        st.error("Invalid credentials.")
        else:
            # ── Show masked recipient list ──────────────────────────────────
            raw = _cfg("email", "OTP_RECIPIENTS", "") or \
                  _cfg("email", "OTP_RECIPIENT",  "jayankgajjala@gmail.com")
            recipients = _parse_recipients(raw)
            masked_list = " &nbsp;·&nbsp; ".join(_mask_email(r) for r in recipients)
            count_label = (
                f"{len(recipients)} recipients"
                if len(recipients) > 1
                else "your inbox"
            )

            st.markdown(f"""
            <div style="background:#0A1828;border:1px solid #1A3A55;border-radius:8px;
                        padding:16px 18px;margin-bottom:16px;font-family:'IBM Plex Mono',monospace">
              <div style="color:#00D4FF;font-size:11px;letter-spacing:0.05em;margin-bottom:6px">
                ✓ OTP DISPATCHED TO {count_label.upper()}
              </div>
              <div style="color:#3A5878;font-size:11px;line-height:1.8">
                {masked_list}
              </div>
            </div>""", unsafe_allow_html=True)

            with st.form("otp_form"):
                entered = st.text_input("Enter 6-digit OTP", max_chars=6)
                verify  = st.form_submit_button("Verify & Access →")
                if verify:
                    elapsed = time.time() - st.session_state.get("otp_timestamp", 0)
                    if elapsed > OTP_EXPIRY:
                        st.error("OTP expired. Refresh and try again.")
                        st.session_state.pop("otp_sent", None)
                        st.rerun()
                    elif entered.strip() == st.session_state.get("otp_value", ""):
                        st.session_state["authenticated"] = True
                        for k in ["otp_sent", "otp_value", "otp_timestamp"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    else:
                        st.error("Invalid OTP.")

            if st.button("← Back"):
                st.session_state.pop("otp_sent", None)
                st.rerun()


def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)
