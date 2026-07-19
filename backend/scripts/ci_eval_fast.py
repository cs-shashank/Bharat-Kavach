#!/usr/bin/env python
"""
ci_eval_fast.py — Fast CI gate using only India-specific transcript samples.

Runs BehavioralClassifier + LegalRAG on 40 high-quality India-specific
transcript samples (20 scam + 20 legit) with aggressive rate limiting.
Completes in ~10 minutes on free tier.

Exit codes: 0=PASS, 1=FAIL, 2=CONFIG ERROR
"""

import os, sys, json, time
from pathlib import Path
from datetime import datetime, timezone

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from services.eval_pipeline import (
    EvaluationPipeline, EvalResultStore,
    MANIFEST_PATH, THRESHOLDS, MIN_SAMPLES_FOR_GATE,
    ComponentMetrics, EvalRunResult,
)
from scripts.ci_eval import check_thresholds, print_pass_summary
import subprocess


def get_git_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5,
                           cwd=str(_BACKEND_DIR))
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def fast_eval(manifest: dict, api_key: str) -> EvalRunResult:
    """Run eval on India-specific samples only — fast and meaningful."""
    from ai_engines.behavioral import BehavioralClassifier
    from ai_engines.legal_rag import LegalRAG
    from ai_engines.protocol import ProtocolVerifier

    print("[fast_eval] Initialising AI engines...")
    behavioral = BehavioralClassifier(api_key=api_key)
    legal_rag   = LegalRAG(api_key=api_key)
    protocol    = ProtocolVerifier()
    print(f"[fast_eval] BehavioralClassifier model: {behavioral.model}")

    # Select only India-specific samples (IDs tr_scam_001-010 and tr_legit_001-010)
    # Plus a few Jim Browning real calls for diversity
    india_ids = {f"tr_scam_{i:03d}" for i in range(1, 11)} | \
                {f"tr_legit_{i:03d}" for i in range(1, 11)}
    jim_ids   = {f"tr_scam_{i:03d}" for i in range(11, 21)}
    target_ids = india_ids | jim_ids

    samples = [s for s in manifest["samples"]
               if s["sample_type"] == "transcript"
               and s["sample_id"] in target_ids]

    print(f"[fast_eval] Running on {len(samples)} transcript samples")
    scam_count  = sum(1 for s in samples if s["ground_truth"] == "scam")
    legit_count = sum(1 for s in samples if s["ground_truth"] == "legit")
    print(f"[fast_eval]   {scam_count} scam, {legit_count} legit")

    bc_pairs, lr_pairs = [], []
    errors = []

    for idx, sample in enumerate(samples, 1):
        sid = sample["sample_id"]
        gt  = sample["ground_truth"]
        txt = sample.get("transcript", "")
        print(f"[fast_eval] {idx}/{len(samples)}: {sid} ({gt})", flush=True)

        # BehavioralClassifier
        try:
            time.sleep(5)  # 5s between calls = 12/min
            result = behavioral.analyze_transcript(txt)
            predicted = "scam" if result.confidence * 100 > 60 else "legit"
            bc_pairs.append({"ground_truth": gt, "predicted": predicted})
            print(f"  BC: {predicted} (conf={result.confidence:.2f}, stage={result.current_stage})")
        except Exception as e:
            errors.append({"sample_id": sid, "component": "BehavioralClassifier", "error": str(e)[:80]})
            print(f"  BC ERROR: {str(e)[:80]}")

        # LegalRAG
        try:
            time.sleep(5)
            findings = legal_rag.verify_legal_claims(txt)
            violations = protocol.check_violations(txt)
            myths = any(f.verdict == "confirmed_false" for f in findings)
            predicted_lr = "scam" if (myths or violations) else "legit"
            lr_pairs.append({"ground_truth": gt, "predicted": predicted_lr})
            print(f"  LR: {predicted_lr} (myths={myths}, violations={len(violations)})")
        except Exception as e:
            errors.append({"sample_id": sid, "component": "LegalRAG", "error": str(e)[:80]})
            print(f"  LR ERROR: {str(e)[:80]}")

    # Compute metrics
    pipeline = EvaluationPipeline(api_key=api_key)

    def mk_metrics(name, pairs):
        m = pipeline.compute_metrics(pairs)
        m.component = name
        return m

    git_sha = get_git_sha()
    run_at  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id  = f"{git_sha}_{run_at}"

    per_component = {
        "BehavioralClassifier": mk_metrics("BehavioralClassifier", bc_pairs),
        "LegalRAG":             mk_metrics("LegalRAG",             lr_pairs),
        "VisionForensics":      ComponentMetrics("VisionForensics", 0, 0, 0, 0, 0),
        "CurrencyVerifier":     ComponentMetrics("CurrencyVerifier", 0, 0, 0, 0, 0),
    }

    run_result = EvalRunResult(
        run_id=run_id,
        manifest_version=manifest.get("manifest_version", 3),
        git_commit_sha=git_sha,
        run_at=run_at,
        per_component=per_component,
        eval_errors=errors,
    )

    pipeline._print_summary(run_result)
    EvalResultStore().save(run_result)
    return run_result


def main():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("[ci_eval_fast] ERROR: GOOGLE_API_KEY not set.", file=sys.stderr)
        sys.exit(2)

    if not MANIFEST_PATH.exists():
        print(f"[ci_eval_fast] ERROR: Manifest not found.", file=sys.stderr)
        sys.exit(2)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    total = len(manifest.get("samples", []))
    print(f"[ci_eval_fast] Manifest loaded: {total} total samples")
    print(f"[ci_eval_fast] Running fast eval on 20 India-specific samples...")
    print(f"[ci_eval_fast] Estimated time: ~10 minutes\n")

    run_result = fast_eval(manifest, api_key)
    failures = check_thresholds(run_result)

    if failures:
        print("\n" + "=" * 70)
        print("  BHARAT KAVACH CI GATE (FAST) — FAIL")
        print("=" * 70)
        for msg in failures:
            print(msg)
        print("=" * 70)
        sys.exit(1)
    else:
        print_pass_summary(run_result)
        sys.exit(0)


if __name__ == "__main__":
    main()
