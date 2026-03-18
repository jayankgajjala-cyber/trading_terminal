"""ui/zerodha_page.py"""
import streamlit as st
from ui.components import page_section, empty_state


def render():
    page_section("Zerodha Kite Connect")

    try:
        from broker.zerodha import get_client
        client = get_client()
    except Exception as e:
        st.error(f"Broker module error: {e}")
        return

    # ── Connection Status ──────────────────────────────────────────────────────
    if client.connected:
        st.markdown("""
        <div style="background:#0A2218;border:1px solid #00C87A33;border-radius:10px;
                    padding:18px 22px;margin-bottom:20px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#00C87A;
                      letter-spacing:0.08em">● CONNECTED</div>
          <div style="color:#2A5040;font-size:12px;margin-top:6px">
            Zerodha Kite Connect is active. Holdings and live prices are available.
          </div>
        </div>""", unsafe_allow_html=True)

        if st.button("Disconnect / Re-authenticate"):
            import os, pathlib
            token_file = "db/zerodha_token.json"
            pathlib.Path(token_file).unlink(missing_ok=True)
            st.rerun()
    else:
        st.markdown("""
        <div style="background:#1A1000;border:1px solid #FFAA0033;border-radius:10px;
                    padding:18px 22px;margin-bottom:20px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#FFAA00;
                      letter-spacing:0.08em">⚠ NOT CONNECTED</div>
          <div style="color:#3A2A00;font-size:12px;margin-top:6px">
            Live portfolio data unavailable. The system is using yfinance for price data.
          </div>
        </div>""", unsafe_allow_html=True)

    # ── Login flow ─────────────────────────────────────────────────────────────
    page_section("Authentication")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#3A5070;
                    line-height:1.8;margin-bottom:16px">
          Step 1 — Click the login link below<br>
          Step 2 — Sign in to your Zerodha account<br>
          Step 3 — Copy the <code style="color:#00D4FF">request_token</code> from the URL<br>
          Step 4 — Paste it below and click Authenticate
        </div>""", unsafe_allow_html=True)

        login_url = client.get_login_url()
        if login_url:
            st.markdown(f"""
            <a href="{login_url}" target="_blank"
               style="display:inline-block;background:#0A1828;color:#00D4FF;
                      border:1px solid #1A3A55;border-radius:7px;padding:9px 18px;
                      font-family:'IBM Plex Mono',monospace;font-size:12px;
                      text-decoration:none;letter-spacing:0.04em">
              Open Zerodha Login →
            </a>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#2A3D58">
              Add ZERODHA_API_KEY to st.secrets to enable Zerodha login.
            </div>""", unsafe_allow_html=True)

    with col2:
        req_token = st.text_input("Request Token", key="zd_req_token",
                                   placeholder="Paste token from redirect URL")
        if st.button("Authenticate →", key="zd_auth_btn", type="primary"):
            if req_token:
                with st.spinner("Generating session..."):
                    ok = client.generate_session(req_token)
                if ok:
                    st.success("Connected successfully!")
                    st.rerun()
                else:
                    st.error("Authentication failed. Check your API credentials.")
            else:
                st.warning("Enter the request token first.")

    # ── API setup guide ────────────────────────────────────────────────────────
    page_section("API Setup Guide")

    st.markdown("""
    <div style="background:#0A0F1C;border:1px solid #141D2E;border-radius:10px;
                padding:20px 22px;font-family:'IBM Plex Mono',monospace;font-size:12px;
                color:#3A5070;line-height:2">
      1. Sign up at <a href="https://developers.kite.trade/" target="_blank"
         style="color:#00D4FF">developers.kite.trade</a><br>
      2. Create a new app → set Redirect URL to
         <code style="color:#FFAA00">https://your-app.streamlit.app</code><br>
      3. Copy API Key and API Secret<br>
      4. Add to Streamlit Cloud Secrets:<br>
         <br>
      <code style="color:#E8EDF5;background:#060A12;padding:12px;display:block;
                    border-radius:6px;border:1px solid #141D2E">
[zerodha]<br>
API_KEY = "your_api_key"<br>
API_SECRET = "your_api_secret"
      </code>
      <br>
      5. Restart the app and authenticate using the flow above.
    </div>""", unsafe_allow_html=True)
