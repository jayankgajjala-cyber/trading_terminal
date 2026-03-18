"""
generate_hash.py — Run this ONCE locally to generate the bcrypt hash for your password.
Then paste the output into st.secrets or .streamlit/secrets.toml as PASSWORD_HASH.

Usage:
    python generate_hash.py
"""
import bcrypt

password = "Jayanju@9498"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
print("\n✅ Copy this value into your secrets as auth.PASSWORD_HASH:\n")
print(hashed)
print()
