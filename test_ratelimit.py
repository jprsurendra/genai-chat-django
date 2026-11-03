import requests
import json
'''
In New Terminal
    $ cd /home/ssr/projects/GenAI/genai-chat-django
    $ source /home/ssr/projects/GenAI/environments/.venv-genai-chat-django/bin/activate
    $ python test_ratelimit.py
Output:
    🔐 Logging in...
    ✅ Login successful! Token acquired.
    
    🚀 Sending 25 requests...
    Request 1: Status 200
    Request 2: Status 200
    ...
    Request 20: Status 200
    Request 21: Status 429   <-----------------   ✅ Rate Limit Hit! (Working as expected)    
'''
# ==========================================
# 1. LOGIN TO GET JWT TOKEN
# ==========================================
BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
CHAT_URL = f"{BASE_URL}/api/chat/stream"

# 🔥 अपने टेस्ट यूज़र के क्रेडेंशियल्स यहाँ डालें
USERNAME = "ssr"
PASSWORD = "ssr"

print("🔐 Logging in...")
login_resp = requests.post(LOGIN_URL, json={
    "username": USERNAME,
    "password": PASSWORD
})

if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
    exit(1)

TOKEN = login_resp.json().get("access")
print(f"✅ Login successful! Token acquired.")

# ==========================================
# 2. SEND 25 REQUESTS TO TEST RATE LIMIT
# ==========================================
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {TOKEN}"
}

print("\n🚀 Sending 25 requests...")
for i in range(1, 26):
    resp = requests.post(CHAT_URL, headers=headers, json={
        "message": "hi",
        "history": [],
        "use_fast": True
    }, stream=True)

    status = resp.status_code
    print(f"Request {i}: Status {status}")

    if status == 429:
        print("\n✅ Rate Limit Hit! (Working as expected)")
        break
    elif status != 200:
        print(f"\n❌ Unexpected error: {resp.text}")
        break