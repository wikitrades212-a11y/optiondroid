"""
schwab_auth.py — one-time local OAuth2 setup for the Schwab Trader API.

Run this script locally (not on Railway) whenever your refresh token expires
(every 7 days) or when setting up the app for the first time.

Usage:
    python schwab_auth.py

You will need:
  - SCHWAB_CLIENT_ID   (App Key from developer.schwab.com)
  - SCHWAB_CLIENT_SECRET (App Secret from developer.schwab.com)
  - Callback URL registered in your app: http://localhost:8182

After running, copy the printed SCHWAB_REFRESH_TOKEN value to Railway Variables.
"""
import base64
import os
import sys
import urllib.parse
import webbrowser

try:
    import httpx
except ImportError:
    sys.exit("Install httpx first:  pip install httpx")

AUTH_URL  = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
# Must be registered as a callback URL in your Schwab developer app.
REDIRECT  = "https://127.0.0.1"


def main():
    client_id = os.environ.get("SCHWAB_CLIENT_ID") or input("SCHWAB_CLIENT_ID (App Key): ").strip()
    client_secret = os.environ.get("SCHWAB_CLIENT_SECRET") or input("SCHWAB_CLIENT_SECRET (App Secret): ").strip()

    if not client_id or not client_secret:
        sys.exit("Both SCHWAB_CLIENT_ID and SCHWAB_CLIENT_SECRET are required.")

    # ── Step 1: Build authorization URL ──────────────────────────────────────
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  REDIRECT,
        "response_type": "code",
        "scope":         "readonly",
    })
    auth_url = f"{AUTH_URL}?{params}"

    print("\n── Schwab OAuth Setup ──────────────────────────────────────────")
    print("Opening browser for Schwab login…")
    print(f"\nIf it does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # ── Step 2: Capture the redirect URL ─────────────────────────────────────
    print("After authorizing, Schwab will redirect to a URL starting with:")
    print(f"  {REDIRECT}/?code=…")
    print("\nPaste the full redirect URL here:")
    redirect_url = input("> ").strip()

    parsed = urllib.parse.urlparse(redirect_url)
    qs = urllib.parse.parse_qs(parsed.query)
    code_list = qs.get("code")
    if not code_list:
        sys.exit(
            "Could not find 'code' in the redirect URL.\n"
            "Make sure you pasted the full URL after being redirected."
        )
    code = code_list[0]

    # ── Step 3: Exchange code for tokens ─────────────────────────────────────
    creds_b64 = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = httpx.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {creds_b64}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": REDIRECT,
        },
    )

    if resp.status_code != 200:
        sys.exit(f"Token exchange failed: HTTP {resp.status_code}\n{resp.text}")

    tokens = resp.json()
    refresh_token = tokens.get("refresh_token", "")
    access_token  = tokens.get("access_token", "")

    if not refresh_token:
        sys.exit(f"No refresh_token in response:\n{tokens}")

    # ── Step 4: Print results ─────────────────────────────────────────────────
    print("\n── Tokens received ─────────────────────────────────────────────")
    print(f"Access token (30 min):  {access_token[:40]}…")
    print(f"\nRefresh token (7 days):\n  {refresh_token}")
    print("\n── Add these to Railway Variables ──────────────────────────────")
    print(f"  SCHWAB_CLIENT_ID      = {client_id}")
    print(f"  SCHWAB_CLIENT_SECRET  = {client_secret}")
    print(f"  SCHWAB_REFRESH_TOKEN  = {refresh_token}")
    print(f"  DATA_PROVIDER         = schwab")
    print("\nRefresh token expires in 7 days. Re-run this script to renew.\n")


if __name__ == "__main__":
    main()
