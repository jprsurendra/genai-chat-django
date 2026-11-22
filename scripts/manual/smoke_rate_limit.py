"""
Manual smoke test: checks the chat rate limit against a RUNNING server.

This is not part of the automated test-suite (see tests/ for that). It sends real requests,
so the LLM is called until the limit is reached.

Usage:
    export SMOKE_USERNAME=<test user>
    export SMOKE_PASSWORD=<test password>
    python scripts/manual/smoke_rate_limit.py            # default: http://127.0.0.1:8000
    SMOKE_BASE_URL=https://staging.example.com python scripts/manual/smoke_rate_limit.py

Expected output:
    Request 1..N: Status 200, then Status 429 -> rate limit works.
"""

import os
import sys

import requests

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
LOGIN_URL = f"{BASE_URL}/api/auth/login"
CHAT_URL = f"{BASE_URL}/api/chat/stream"
TIMEOUT_SECONDS = 60
MAX_REQUESTS = int(os.getenv("SMOKE_MAX_REQUESTS", "25"))


def main() -> int:
    username = os.getenv("SMOKE_USERNAME")
    password = os.getenv("SMOKE_PASSWORD")
    if not username or not password:
        print("Set SMOKE_USERNAME and SMOKE_PASSWORD (credentials are never hardcoded).")
        return 2

    print("🔐 Logging in...")
    login_resp = requests.post(LOGIN_URL, json={"username": username, "password": password}, timeout=TIMEOUT_SECONDS)
    if login_resp.status_code != 200:
        print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
        return 1

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {login_resp.json()['access']}"}
    print("✅ Login successful! Token acquired.")

    print(f"\n🚀 Sending up to {MAX_REQUESTS} requests...")
    for i in range(1, MAX_REQUESTS + 1):
        resp = requests.post(
            CHAT_URL, headers=headers, json={"message": "hi", "use_fast": True}, stream=True, timeout=TIMEOUT_SECONDS
        )
        print(f"Request {i}: Status {resp.status_code}")
        resp.close()

        if resp.status_code == 429:
            print("\n✅ Rate Limit Hit! (Working as expected)")
            return 0
        if resp.status_code != 200:
            print(f"\n❌ Unexpected error: {resp.text}")
            return 1

    print("\n⚠️ The limit was not reached. Check CHAT_RATE_LIMIT.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
