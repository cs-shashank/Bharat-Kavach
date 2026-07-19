#!/usr/bin/env python
"""
ci_eval_quick.py — Bharat Kavach Quick CI Gate
Runs on a stratified sample (max 20 transcripts, 10 currency, 10 documents)
to produce real metrics within Gemini free-tier rate limits (~15 req/min).

Usage:
  python backend/scripts/ci_eval_quick.py

Exit codes: 0=PASS, 1=FAIL, 2=CONFIG ERROR
"""

import os, sys, json, random
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from services.eval_pipeline import (
    EvaluationPipeline,
    EvalResultStore,
    MANIFEST_PATH,
    THRESHOLDS,
    MIN_SAMPLES_FOR_GATE,
)
from scripts.ci_eval import check_thresholds, print_pass_summary


def build_quick_manifest(manifest: dict, max_transcripts: int = 20,
                          max_per_image_class: int = 10) -> dict:
    """Return a reduced manifest: stratified sample for fast evaluation."""
    samples = manifest["samples"]

    # Transcripts: equal split scam/legit, prefer India-specific + tricky negatives
    scam = [s for s in samples if s["sample_type"] == "transcript" and s["ground_truth"] == "scam"]
    legit = [s for s in samples if s["sample_type"] == "transcript" and s["ground_truth"] == "legit"]
    tricky = [s for s in legit if s.get("tricky_negative")]

    # Prefer India-specific (IDs tr_scam_001..010 and tr_legit_001..010) + tricky negatives
    india_scam = [s for s in scam if s["sample_id"].startswith("tr_scam_0")][:10]
    india_legit = [s for s in legit if s["sample_id"].startswith("tr_legit_0")][:7]
    selected_legit = list({s["sample_id"]: s for s in tricky + india_legit}.values())[:10]
    selected_scam = india_scam[:10]

    # Image samples: up to max_per_image_class per class
    random.seed(42)
    cur_genuine    = random.sample([s for s in samples if s["sample_type"]=="currency_image" and s["ground_truth"]=="genuine"],
                                   min(max_per_image_class, len([s for s in samples if s["sample_type"]=="currency_image" and s["ground_truth"]=="genuine"])))
    cur_fake       = random.sample([s for s in samples if s["sample_type"]=="currency_image" and s["ground_truth"]=="counterfeit"],
                                   min(max_per_image_class, len([s for s in samples if s["sample_type"]=="currency_image" and s["ground_truth"]=="counterfeit"])))
    doc_authentic  = random.sample([s for s in samples if s["sample_type"]=="document_image" and s["ground_truth"]=="authentic"],
                                   min(max_per_image_class, len([s for s in samples if s["sample_type"]=="document_image" and s["ground_truth"]=="authentic"])))
    doc_forged     = random.sample([s for s in samples if s["sample_type"]=="document_image" and s["ground_truth"]=="forged"],
                                   min(max_per_image_class, len([s for s in samples if s["sample_type"]=="document_image" and s["ground_truth"]=="forged"])))

    quick = dict(manifest)
    quick["samples"] = selected_scam + selected_legit + cur_genuine + cur_fake + doc_authentic + doc_forged

    from collections import Counter
    by = Counter(f"{s['sample_type']}:{s['ground_truth']}" for s in quick["samples"])
    print("[ci_eval_quick] Quick manifest sample counts:")
    for k, v in sorted(by.items()):
        print(f"  {k}: {v}")
    print(f"  Total: {len(quick['samples'])}")

    return quick


def main():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("[ci_eval_quick] ERROR: GOOGLE_API_KEY not set.", file=sys.stderr)
        sys.exit(2)

    if not MANIFEST_PATH.exists():
        print(f"[ci_eval_quick] ERROR: Manifest not found at {MANIFEST_PATH}.", file=sys.stderr)
        sys.exit(2)

    print("[ci_eval_quick] Loading manifest...")
    pipeline = EvaluationPipeline(api_key=api_key)
    manifest = pipeline.load_manifest()

    quick_manifest = build_quick_manifest(manifest)

    print("[ci_eval_quick] Running evaluation on quick sample...")
    run_result = pipeline.run(quick_manifest)

    failures = check_thresholds(run_result)

    if failures:
        print("\n" + "=" * 70)
        print("  BHARAT KAVACH CI GATE (QUICK) — FAIL")
        print("=" * 70)
        for msg in failures:
            print(msg)
        print("=" * 70)
        print(f"  Run ID: {run_result.run_id}")
        print("=" * 70 + "\n")
        sys.exit(1)
    else:
        print_pass_summary(run_result)
        sys.exit(0)


if __name__ == "__main__":
    main()
