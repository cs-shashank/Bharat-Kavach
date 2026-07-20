"""Test AQ. key format with latest google-genai SDK."""
import os
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("GOOGLE_API_KEY", "")
print(f"Key prefix: {key[:10]}...")
print(f"google-genai version:", end=" ")

import google.genai
print(google.genai.__version__)

from google import genai
from google.genai import types

# Method 1: standard api_key
print("\nTesting standard api_key method...")
try:
    client = genai.Client(api_key=key)
    r = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents="Say the word WORKING in capitals only"
    )
    print("✅ SUCCESS:", r.text.strip())
except Exception as e:
    print(f"❌ Failed: {str(e)[:200]}")

# Method 2: as authorization header
print("\nTesting Authorization header method...")
try:
    client2 = genai.Client(
        http_options=types.HttpOptions(
            headers={"x-goog-api-key": key}
        )
    )
    r2 = client2.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents="Say the word WORKING in capitals only"
    )
    print("✅ SUCCESS:", r2.text.strip())
except Exception as e:
    print(f"❌ Failed: {str(e)[:200]}")
