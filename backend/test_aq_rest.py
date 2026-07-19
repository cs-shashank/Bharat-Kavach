"""Test AQ. key directly via HTTP to find the right endpoint."""
import urllib.request, json, os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GOOGLE_API_KEY", "")
print(f"Key prefix: {key[:10]}...")

body = json.dumps({
    "contents": [{"parts": [{"text": "Say WORKING"}]}]
}).encode()

# Test 1: Standard API key endpoint
print("\n--- Test 1: Standard key endpoint ---")
try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=15)
    print("✅ SUCCESS:", json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"][:50])
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"❌ Error: {str(e)[:200]}")

# Test 2: Bearer token endpoint  
print("\n--- Test 2: Bearer token endpoint ---")
try:
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    })
    r = urllib.request.urlopen(req, timeout=15)
    print("✅ SUCCESS:", json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"][:50])
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"❌ Error: {str(e)[:200]}")

# Test 3: New AI Platform endpoint with Bearer
print("\n--- Test 3: aiplatform endpoint with Bearer ---")
try:
    url = "https://aiplatform.googleapis.com/v1/projects/gen-lang-client-0145842577/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent"
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    })
    r = urllib.request.urlopen(req, timeout=15)
    print("✅ SUCCESS:", json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"][:50])
except urllib.error.HTTPError as e:
    print(f"❌ HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"❌ Error: {str(e)[:200]}")
