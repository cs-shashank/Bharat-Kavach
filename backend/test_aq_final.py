"""Test AQ. key using GEMINI_API_KEY env var — SDK auto-detects format."""
import os
from dotenv import load_dotenv
load_dotenv()

# Let SDK pick up GEMINI_API_KEY automatically
from google import genai

print(f"google-genai version: {genai.__version__}")
print(f"GEMINI_API_KEY set: {bool(os.getenv('GEMINI_API_KEY'))}")
print(f"Key prefix: {os.getenv('GEMINI_API_KEY','')[:10]}...")

# Method: no explicit api_key — SDK reads GEMINI_API_KEY automatically
print("\nTesting SDK auto-detect from GEMINI_API_KEY...")
try:
    client = genai.Client()
    r = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents="Reply with one word: WORKING"
    )
    print(f"✅ SUCCESS: {r.text.strip()}")
except Exception as e:
    print(f"❌ Failed: {str(e)[:300]}")

# Also test with gemini-2.5-flash as mentioned
print("\nTesting gemini-2.5-flash...")
try:
    client2 = genai.Client()
    r2 = client2.models.generate_content(
        model="gemini-2.5-flash",
        contents="Reply with one word: WORKING"
    )
    print(f"✅ SUCCESS: {r2.text.strip()}")
except Exception as e:
    print(f"❌ Failed: {str(e)[:300]}")
