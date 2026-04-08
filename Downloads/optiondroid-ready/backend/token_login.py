"""
Create a Robinhood session from a browser-extracted access token.
Usage: python token_login.py <access_token>

Get the token from Safari/Chrome DevTools:
  Safari: Develop → Show Web Inspector → Storage → Local Storage → robinhood.com → access_token
  Chrome: F12 → Application → Local Storage → robinhood.com → access_token
"""
import sys, os, pickle, requests
from robin_stocks.robinhood.authentication import generate_device_token
from robin_stocks.robinhood.helper import update_session, set_login_state

PICKLE_PATH = os.path.expanduser("~/.tokens/robinhood.pickle")


def main():
    if len(sys.argv) < 2:
        print("Usage: python token_login.py <access_token>")
        print()
        print("Get token from browser DevTools → Storage → Local Storage → robinhood.com → access_token")
        sys.exit(1)

    token = sys.argv[1].strip()

    # Verify the token works
    print("Verifying token...")
    r = requests.get(
        "https://api.robinhood.com/accounts/",
        headers={"Authorization": f"Bearer {token}"}
    )

    if r.status_code != 200:
        print(f"Token invalid (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)

    print(f"✓ Token valid — account data received")

    # Save session pickle
    os.makedirs(os.path.dirname(PICKLE_PATH), exist_ok=True)
    device_token = generate_device_token()
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump({
            "token_type":    "Bearer",
            "access_token":  token,
            "refresh_token": "",
            "device_token":  device_token,
        }, f)

    update_session("Authorization", f"Bearer {token}")
    set_login_state(True)

    print(f"✓ Session saved → {PICKLE_PATH}")
    print("\n✓ Done! The backend will use this token automatically.")
    print("  (Tokens typically last 24 hours — re-run this if it expires)")


if __name__ == "__main__":
    main()
