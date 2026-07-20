"""Test AQ. key as Authorization Bearer header directly."""
import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GOOGLE_API_KEY", "")
print(f"Key: {key[:15]}...")

body = json.dumps({
    "contents": [{"parts": [{"text": "Reply with one word: WORKING"}]}]
}).encode()

# The AQ. key IS an OAuth2 token - try it as Authorization Bearer
# on the standard generativelanguage endpoint
print("\n--- Test: Bearer on generativelanguage ---")
try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    })
    r = urllib.request.urlopen(req, timeout=15)
    result = json.loads(r.read())
    print("✅ SUCCESS:", result["candidates"][0]["content"]["parts"][0]["text"].strip())
except urllib.error.HTTPError as e:
    err = json.loads(e.read().decode())
    print(f"❌ HTTP {e.code}: {err.get('error',{}).get('message','')[:200]}")

# Try on v1 (not beta)
print("\n--- Test: Bearer on v1 ---")
try:
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    })
    r = urllib.request.urlopen(req, timeout=15)
    result = json.loads(r.read())
    print("✅ SUCCESS:", result["candidates"][0]["content"]["parts"][0]["text"].strip())
except urllib.error.HTTPError as e:
    err = json.loads(e.read().decode())
    print(f"❌ HTTP {e.code}: {err.get('error',{}).get('message','')[:200]}")

# Try with x-goog-api-key header
print("\n--- Test: x-goog-api-key header ---")
try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "x-goog-api-key": key
    })
    r = urllib.request.urlopen(req, timeout=15)
    result = json.loads(r.read())
    print("✅ SUCCESS:", result["candidates"][0]["content"]["parts"][0]["text"].strip())
except urllib.error.HTTPError as e:
    err = json.loads(e.read().decode())
    print(f"❌ HTTP {e.code}: {err.get('error',{}).get('message','')[:200]}")
