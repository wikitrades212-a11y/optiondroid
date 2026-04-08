"""
Two-phase Robinhood login.

Phase 1 (automatic): Sends login → gets workflow ID → saves device token → exits.
Phase 2 (automatic): Reads saved device token → retries login → saves session.

Run: python save_login.py
     (approve in Robinhood app when prompted)
     python save_login.py  ← run again after approving
"""
import time, sys, requests, pickle, os, json
from robin_stocks.robinhood.authentication import generate_device_token
from robin_stocks.robinhood.helper import update_session, set_login_state

LOGIN_URL  = "https://api.robinhood.com/oauth2/token/"
CLIENT_ID  = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"
STATE_FILE = "/tmp/rh_login_state.json"
PICKLE_PATH = os.path.expanduser("~/.tokens/robinhood.pickle")


def login_request(username, password, device_token, mfa_code=None):
    payload = {
        "client_id": CLIENT_ID, "expires_in": 86400,
        "grant_type": "password", "password": password,
        "scope": "internal", "username": username,
        "challenge_type": "sms", "device_token": device_token,
    }
    if mfa_code:
        payload["mfa_code"] = mfa_code
    return requests.post(LOGIN_URL, data=payload).json()


def respond_to_challenge(challenge_id, code):
    r = requests.post(
        f"https://api.robinhood.com/challenge/{challenge_id}/respond/",
        data={"response": code}
    )
    return r.json()


def save_session(data, device_token):
    os.makedirs(os.path.dirname(PICKLE_PATH), exist_ok=True)
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump({
            "token_type":    data["token_type"],
            "access_token":  data["access_token"],
            "refresh_token": data["refresh_token"],
            "device_token":  device_token,
        }, f)
    update_session("Authorization", f"{data['token_type']} {data['access_token']}")
    set_login_state(True)
    print(f"\n  Session saved → {PICKLE_PATH}")
    print("  Backend will reuse this automatically. No restart needed.")


def handle_success(data, device_token):
    save_session(data, device_token)
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
    print("\n✓ LOGIN SUCCESSFUL — the backend is now authenticated!\n")
    sys.exit(0)


def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    username = os.getenv("RH_USERNAME", "")
    password = os.getenv("RH_PASSWORD", "")

    # ── Phase 2: retry with saved device token ────────────────────────────────
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)
        device_token = state["device_token"]
        print(f"Retrying login with saved device token...")
        print(f"(If you haven't approved yet, approve in the Robinhood app NOW)\n")

        data = login_request(username, password, device_token)

        if "access_token" in data:
            handle_success(data, device_token)

        elif "verification_workflow" in data:
            status = data["verification_workflow"]["workflow_status"]
            wid    = data["verification_workflow"]["id"]
            print(f"Still pending (status: {status})")
            print(f"Workflow ID: {wid}\n")
            print("The approval hasn't registered yet. Options:")
            print("  1. Make sure you approved the LATEST entry in the Robinhood app")
            print("     Account → Security → Login Requests — approve the newest one")
            print("  2. Wait 30 seconds then run: python save_login.py")
            sys.exit(1)

        elif "challenge" in data:
            # SMS/email challenge
            cid  = data["challenge"]["id"]
            code = input("Enter the Robinhood SMS/email code: ").strip()
            res  = respond_to_challenge(cid, code)
            r    = requests.post(LOGIN_URL, data={
                "client_id": CLIENT_ID, "expires_in": 86400,
                "grant_type": "password", "password": password,
                "scope": "internal", "username": username,
                "challenge_type": "sms", "device_token": device_token,
            }, headers={"X-ROBINHOOD-CHALLENGE-RESPONSE-ID": cid})
            data = r.json()
            if "access_token" in data:
                handle_success(data, device_token)
            else:
                print(f"Failed: {data}")
                sys.exit(1)

        elif "mfa_required" in data:
            code = input("Enter MFA code: ").strip()
            data = login_request(username, password, device_token, mfa_code=code)
            if "access_token" in data:
                handle_success(data, device_token)
            else:
                print(f"MFA failed: {data}")
                sys.exit(1)

        else:
            print(f"Unexpected response: {data}")
            sys.exit(1)

    # ── Phase 1: initial login → get workflow ID ──────────────────────────────
    else:
        device_token = generate_device_token()
        print(f"Logging in as {username}...")
        data = login_request(username, password, device_token)

        if "access_token" in data:
            handle_success(data, device_token)

        elif "verification_workflow" in data:
            wid    = data["verification_workflow"]["id"]
            status = data["verification_workflow"]["workflow_status"]

            # Save device token for Phase 2
            with open(STATE_FILE, "w") as f:
                json.dump({"device_token": device_token, "workflow_id": wid}, f)

            print("\n" + "═" * 60)
            print("  ACTION REQUIRED ON YOUR PHONE")
            print("═" * 60)
            print(f"  Workflow ID: {wid}")
            print()
            print("  1. Open the Robinhood app RIGHT NOW")
            print("  2. Tap Account (bottom right) → Security")
            print("  3. Find 'Login Requests' or 'Active Sessions'")
            print("  4. Approve the NEWEST pending entry")
            print()
            print("  After approving, run this script again:")
            print("  python save_login.py")
            print("═" * 60)
            sys.exit(0)   # clean exit — wait for user

        else:
            print(f"Unexpected response: {data}")
            sys.exit(1)


if __name__ == "__main__":
    main()
