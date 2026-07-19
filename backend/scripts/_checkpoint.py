"""Phase 1 final checkpoint verification script."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []

# 1. evidence_bundle.schema.json
try:
    with open("schemas/evidence_bundle.schema.json") as f:
        s = json.load(f)
    results.append(("schema.json valid JSON", True, f"{len(s['required'])} required fields"))
except Exception as e:
    results.append(("schema.json valid JSON", False, str(e)))

# 2. eval_manifest.json
try:
    with open("data/eval_manifest.json") as f:
        m = json.load(f)
    transcripts = [s for s in m["samples"] if s["sample_type"] == "transcript"]
    results.append(("manifest_version present", "manifest_version" in m, ""))
    results.append((f"transcript count >= 20", len(transcripts) >= 20, f"found {len(transcripts)}"))
    tricky = [s for s in transcripts if s.get("tricky_negative")]
    results.append((f"tricky_negative >= 3", len(tricky) >= 3, f"found {len(tricky)}"))
except Exception as e:
    results.append(("eval_manifest.json", False, str(e)))

# 3. legal_kb.json
try:
    with open("data/legal_kb.json") as f:
        kb = json.load(f)
    results.append(("legal_kb 10+ entries", len(kb) >= 10, f"{len(kb)} entries"))
    all_bns = all("bns_verified" in e and "verified_by" in e and "verified_date" in e for e in kb)
    results.append(("all entries have bns_verified+verified_by+verified_date", all_bns, ""))
    ipc_free = not any("IPC" in str(e) or "CrPC" in str(e) for e in kb)
    results.append(("no IPC/CrPC references", ipc_free, ""))
except Exception as e:
    results.append(("legal_kb.json", False, str(e)))

# 4. EvidenceExporter
try:
    from services.evidence_exporter import EvidenceExporter, EvidenceBundle
    results.append(("EvidenceExporter importable", True, ""))
except Exception as e:
    results.append(("EvidenceExporter importable", False, str(e)))

# 5. EvalPipeline
try:
    from services.eval_pipeline import EvaluationPipeline, EvalResultStore, ComponentMetrics, EvalRunResult
    results.append(("EvalPipeline importable", True, ""))
except Exception as e:
    results.append(("EvalPipeline importable", False, str(e)))

# 6. ci_eval.py
try:
    import scripts.ci_eval
    results.append(("ci_eval.py importable", True, ""))
except Exception as e:
    results.append(("ci_eval.py importable", False, str(e)))

# 7. git SHA
try:
    r = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, timeout=5,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    sha = r.stdout.strip()
    is_real = bool(sha) and sha != "unknown"
    results.append(("git SHA is real (not 'unknown')", is_real, sha or "EMPTY — fix git before citing metrics"))
except Exception as e:
    results.append(("git SHA check", False, str(e)))

# 8. evidence endpoints in main.py
try:
    import ast
    with open("main.py") as f:
        tree = ast.parse(f.read())
    fns = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
    has_ev = "get_case_evidence" in fns and "download_case_evidence_pdf" in fns
    results.append(("evidence endpoints in main.py", has_ev, ""))
except Exception as e:
    results.append(("evidence endpoints", False, str(e)))

# Print summary
print()
print("=" * 65)
print("  BHARAT KAVACH PHASE 1 — FINAL CHECKPOINT")
print("=" * 65)
for label, ok, detail in results:
    status = "PASS" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")
print("=" * 65)
failures = [label for label, ok, _ in results if not ok]
if failures:
    print(f"  {len(failures)} FAILED check(s) — see above")
    sys.exit(1)
else:
    print("  ALL CHECKS PASSED — Phase 1 complete")
    sys.exit(0)
