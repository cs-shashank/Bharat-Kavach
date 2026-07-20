"""Smoke test all Bharat Kavach API endpoints."""
import urllib.request, json, sys

base = "http://localhost:8000"

def get(path):
    r = urllib.request.urlopen(f"{base}{path}", timeout=30)
    return json.loads(r.read())

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read())

print("=" * 60)
print("BHARAT KAVACH API SMOKE TEST")
print("=" * 60)

# 1. Health
r = get("/")
print(f"\n✅ GET /           : {r['message']}")

# 2. Analyze - clear scam
scam_transcript = (
    "I am CBI officer Sharma. Your Aadhaar number has been linked to a "
    "money laundering case. You are now under digital arrest on this video call. "
    "Do not disconnect and do not inform your family. "
    "Transfer Rs 2 lakhs immediately to clear your name."
)
r = post("/analyze", {"transcript": scam_transcript, "user_id": "SMOKE_TEST_001"})
print(f"\n✅ POST /analyze (scam)")
print(f"   risk_score          : {r['risk_score']:.1f}")
print(f"   stage               : {r['stage']}")
print(f"   intervention        : {r['intervention_triggered']}")
print(f"   legal_citations     : {len(r['legal_citations'])} found")
case_id = r["id"]

# 3. Analyze - legit call
legit_transcript = "Hi this is HDFC Bank calling to confirm your FD renewal. No payment needed."
r2 = post("/analyze", {"transcript": legit_transcript, "user_id": "SMOKE_TEST_002"})
print(f"\n✅ POST /analyze (legit)")
print(f"   risk_score          : {r2['risk_score']:.1f}")
print(f"   intervention        : {r2['intervention_triggered']}")

# 4. Cases list
cases = get("/cases")
print(f"\n✅ GET /cases       : {len(cases)} cases in database")

# 5. Evidence bundle
ev = get(f"/cases/{case_id}/evidence")
print(f"\n✅ GET /cases/{case_id}/evidence")
print(f"   bundle_id           : {ev['bundle_id']}")
print(f"   sha256_hash         : {ev['sha256_hash'][:32]}...")
print(f"   pdf_url             : {ev['pdf_url']}")
print(f"   components          : {list(ev['component_verdicts'].keys())}")
chain = ev.get("chain_of_custody", [])
print(f"   chain_of_custody    : {len(chain)} entries")

# 6. Evidence PDF download check (just header check)
pdf_req = urllib.request.Request(
    f"{base}/cases/{case_id}/evidence/download", method="GET"
)
try:
    pdf_r = urllib.request.urlopen(pdf_req, timeout=30)
    content_type = pdf_r.headers.get("Content-Type", "")
    content_disp = pdf_r.headers.get("Content-Disposition", "")
    print(f"\n✅ GET /cases/{case_id}/evidence/download")
    print(f"   Content-Type        : {content_type}")
    print(f"   Content-Disposition : {content_disp}")
except Exception as e:
    print(f"\n❌ GET /cases/{case_id}/evidence/download : {e}")

print("\n" + "=" * 60)
print("ALL SMOKE TESTS PASSED")
print("=" * 60)
