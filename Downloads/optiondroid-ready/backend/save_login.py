"""
Two-phase Robinhood login with stale-workflow detection and optional polling.

Phase 1 (automatic): Sends login → gets workflow ID → saves device token + workflow ID → exits.
Phase 2 (automatic): Reads saved state → retries login → saves session pickle.

Usage:
  python save_login.py              # normal run
  python save_login.py --reset      # discard saved state, start fresh
  python save_login.py --poll       # phase 2 with automatic retry loop
  python save_login.py --reset --poll
"""

import argparse
import base64
import json
import os
import pickle
import sys
import time

import requests
from robin_stocks.robinhood.authentication import generate_device_token
from robin_stocks.robinhood.helper import update_session, set_login_state

LOGIN_URL   = "https://api.robinhood.com/oauth2/token/"
CLIENT_ID   = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS"
STATE_FILE  = "/tmp/rh_login_state.json"
PICKLE_PATH = os.path.expanduser("~/.tokens/robinhood.pickle")


# ── helpers ────────────────────────────────────────────────────────────────────

def login_request(username, password, device_token, mfa_code=None):
    payload = {
        "client_id":      CLIENT_ID,
        "expires_in":     86400,
        "grant_type":     "password",
        "password":       password,
        "scope":          "internal",
        "username":       username,
        "challenge_type": "sms",
        "device_token":   device_token,
    }
    if mfa_code:
        payload["mfa_code"] = mfa_code
    return requests.post(LOGIN_URL, data=payload).json()


def respond_to_challenge(challenge_id, code):
    r = requests.post(
        f"https://api.robinhood.com/challenge/{challenge_id}/respond/",
        data={"response": code},
    )
    return r.json()


def save_session(data, device_token):
    os.makedirs(os.path.dirname(PICKLE_PATH), exist_ok=True)
    payload = {
        "token_type":    data["token_type"],
        "access_token":  data["access_token"],
        "refresh_token": data["refresh_token"],
        "device_token":  device_token,
    }
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(payload, f)

    # Verify the file was actually written
    if not os.path.exists(PICKLE_PATH):
        print(f"\n✗ ERROR: pickle file was not written to {PICKLE_PATH}")
        sys.exit(1)

    update_session("Authorization", f"{data['token_type']} {data['access_token']}")
    set_login_state(True)
    print(f"\n  Pickle saved → {PICKLE_PATH}  ({os.path.getsize(PICKLE_PATH)} bytes)")

    # Print the base64-encoded pickle so it can be pasted into Railway
    with open(PICKLE_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    print()
    print("  ── RH_PICKLE_B64 for Railway ──────────────────────────────────────")
    print("  Copy the value below into Railway → Variables → RH_PICKLE_B64:")
    print()
    print(f"  {encoded}")
    print()
    print("  Also set DATA_PROVIDER=robinhood in Railway Variables.")
    print("  ──────────────────────────────────────────────────────────────────")


def handle_success(data, device_token):
    save_session(data, device_token)
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print(f"  State file {STATE_FILE} removed.")
    print("\n✓ LOGIN SUCCESSFUL — the backend is now authenticated!\n")
    sys.exit(0)


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(device_token, workflow_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"device_token": device_token, "workflow_id": workflow_id}, f)


def print_separator():
    print("═" * 60)


# ── phase 2: retry with saved state ───────────────────────────────────────────

def phase2(username, password, state, poll=False):
    device_token = state["device_token"]
    saved_wid    = state.get("workflow_id", "<unknown>")

    print(f"  Saved workflow ID : {saved_wid}")
    print(f"  Device token      : {device_token[:8]}…")
    print()

    def attempt():
        data = login_request(username, password, device_token)

        if "access_token" in data:
            handle_success(data, device_token)  # exits

        elif "verification_workflow" in data:
            wf     = data["verification_workflow"]
            wid    = wf["id"]
            status = wf.get("workflow_status", "unknown")

            if wid != saved_wid:
                print(f"\n  ⚠  New workflow ID returned: {wid}")
                print(f"     (was: {saved_wid})")
                print("  Updating saved state with new workflow ID.")
                save_state(device_token, wid)
            else:
                print(f"  Reusing OLD workflow  →  status: {status}")

            return status  # caller decides what to do

        elif "challenge" in data:
            cid  = data["challenge"]["id"]
            code = input("Enter the Robinhood SMS/email code: ").strip()
            respond_to_challenge(cid, code)
            r = requests.post(LOGIN_URL, data={
                "client_id":      CLIENT_ID,
                "expires_in":     86400,
                "grant_type":     "password",
                "password":       password,
                "scope":          "internal",
                "username":       username,
                "challenge_type": "sms",
                "device_token":   device_token,
            }, headers={"X-ROBINHOOD-CHALLENGE-RESPONSE-ID": cid})
            d = r.json()
            if "access_token" in d:
                handle_success(d, device_token)  # exits
            else:
                print(f"Challenge failed: {d}")
                sys.exit(1)

        elif "mfa_required" in data:
            code = input("Enter MFA code: ").strip()
            d    = login_request(username, password, device_token, mfa_code=code)
            if "access_token" in d:
                handle_success(d, device_token)  # exits
            else:
                print(f"MFA failed: {d}")
                sys.exit(1)

        else:
            print(f"Unexpected response: {data}")
            sys.exit(1)

        return None

    if not poll:
        status = attempt()
        if status is not None:
            print()
            print("  The approval hasn't registered yet. Options:")
            print("    1. Approve the LATEST entry in the Robinhood app:")
            print("       Account → Security → Login Requests")
            print("    2. Run with --poll to wait automatically:")
            print("       python save_login.py --poll")
            print("    3. Run with --reset to start over:")
            print("       python save_login.py --reset")
        sys.exit(1)

    # ── polling loop ──────────────────────────────────────────────────────────
    print("  Polling every 10 s — approve in the Robinhood app now.")
    print("  (Ctrl-C to stop)\n")
    interval = 10
    elapsed  = 0
    while True:
        status = attempt()   # exits on success
        if status is not None:
            elapsed += interval
            print(f"  Still pending ({status}) — {elapsed}s elapsed, retrying in {interval}s…")
            time.sleep(interval)
        # attempt() calls sys.exit(0) on success, so we never reach here on success


# ── phase 1: fresh login → get workflow ID ─────────────────────────────────────

def phase1(username, password):
    device_token = generate_device_token()
    print(f"  Device token : {device_token[:8]}…")
    print(f"  Username     : {username}")
    print()
    print("  Sending login request…")
    data = login_request(username, password, device_token)

    if "access_token" in data:
        handle_success(data, device_token)  # exits immediately (no 2FA needed)

    elif "verification_workflow" in data:
        wid    = data["verification_workflow"]["id"]
        status = data["verification_workflow"].get("workflow_status", "unknown")

        save_state(device_token, wid)

        print()
        print_separator()
        print("  ACTION REQUIRED ON YOUR PHONE")
        print_separator()
        print(f"  Workflow ID : {wid}")
        print(f"  Status      : {status}")
        print()
        print("  1. Open the Robinhood app RIGHT NOW")
        print("  2. Tap Account (bottom right) → Security")
        print("  3. Find 'Login Requests' or 'Active Sessions'")
        print("  4. Approve the NEWEST pending entry")
        print()
        print("  After approving, run:")
        print("    python save_login.py          # check once")
        print("    python save_login.py --poll   # keep retrying until approved")
        print_separator()
        sys.exit(0)

    else:
        print(f"Unexpected response: {data}")
        sys.exit(1)


# ── entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Robinhood two-phase login")
    parser.add_argument("--reset", action="store_true",
                        help="Discard saved state and start a fresh login")
    parser.add_argument("--poll", action="store_true",
                        help="In phase 2, poll every 10 s until approved")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    username = os.getenv("RH_USERNAME", "")
    password = os.getenv("RH_PASSWORD", "")

    if not username or not password:
        print("✗ RH_USERNAME / RH_PASSWORD not set in .env")
        sys.exit(1)

    if args.reset and os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)
        print(f"  --reset: removed {STATE_FILE}")

    state = load_state()

    if state:
        print_separator()
        print("  PHASE 2 — resuming saved login state")
        print_separator()
        phase2(username, password, state, poll=args.poll)
    else:
        print_separator()
        print("  PHASE 1 — starting fresh login")
        print_separator()
        phase1(username, password)


if __name__ == "__main__":
    main()
