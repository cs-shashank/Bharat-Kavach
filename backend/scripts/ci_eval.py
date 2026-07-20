#!/usr/bin/env python
"""
ci_eval.py — Bharat Kavach Phase 1 CI Quality Gate

Runs the EvaluationPipeline against the current EvalManifest and exits
non-zero if any component falls below its threshold.

Exit codes:
  0 — all threshold checks passed
  1 — one or more threshold checks failed
  2 — configuration error (missing GOOGLE_API_KEY, missing manifest)

Usage:
  python backend/scripts/ci_eval.py

Environment:
  GOOGLE_API_KEY — required for live AI engine evaluation
"""

import os
import sys
from pathlib import Path

# Ensure backend/ is on sys.path regardless of cwd
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from services.eval_pipeline import (
    EvaluationPipeline,
    EvalResultStore,
    MANIFEST_PATH,
    THRESHOLDS,
    MIN_SAMPLES_FOR_GATE,
)


def check_thresholds(run_result) -> list:
    """
    Compare per-component metrics against THRESHOLDS.
    Returns a list of failure strings (empty = all passed).
    Skips threshold check when sample_count < MIN_SAMPLES_FOR_GATE.
    """
    failures = []

    for component, thresholds in THRESHOLDS.items():
        metrics = run_result.per_component.get(component)
        if metrics is None:
            print(f"  WARNING: No metrics found for {component} — skipping gate")
            continue

        if metrics.sample_count < MIN_SAMPLES_FOR_GATE:
            print(
                f"  WARNING: insufficient data for {component} "
                f"(sample_count={metrics.sample_count} < {MIN_SAMPLES_FOR_GATE}); "
                f"skipping gate"
            )
            continue

        # Check precision
        if "precision" in thresholds and metrics.precision < thresholds["precision"]:
            failures.append(
                f"  FAIL {component}: precision={metrics.precision:.3f} "
                f"< threshold={thresholds['precision']:.2f}"
            )

        # Check FPR (lower is better, so fail if above threshold)
        if "fpr" in thresholds and metrics.fpr > thresholds["fpr"]:
            failures.append(
                f"  FAIL {component}: fpr={metrics.fpr:.3f} "
                f"> threshold={thresholds['fpr']:.2f}"
            )

    return failures


def print_pass_summary(run_result):
    """Print the PASS summary table."""
    print("\n" + "=" * 70)
    print("  BHARAT KAVACH CI GATE — PASS")
    print("=" * 70)
    header = f"  {'Component':<25} {'Precision':>10} {'FPR':>7}  Threshold"
    print(header)
    print("-" * 70)

    for component, thresholds in THRESHOLDS.items():
        metrics = run_result.per_component.get(component)
        if metrics is None or metrics.sample_count < MIN_SAMPLES_FOR_GATE:
            print(f"  {component:<25}  {'(skipped)':>10}")
            continue

        p_str   = f"{metrics.precision:.3f}"
        fpr_str = f"{metrics.fpr:.3f}" if "fpr" in thresholds else "  —  "
        thresh  = f"P≥{thresholds['precision']:.2f}"
        if "fpr" in thresholds:
            thresh += f" / FPR≤{thresholds['fpr']:.2f}"
        print(f"  {component:<25} {p_str:>10} {fpr_str:>7}  {thresh}  ✓")

    print("=" * 70)
    print(f"  Run ID: {run_result.run_id}")
    print("=" * 70 + "\n")


def main():
    # Step 1: Verify GOOGLE_API_KEY
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("[ci_eval] ERROR: GOOGLE_API_KEY is not set. Cannot run evaluation.", file=sys.stderr)
        sys.exit(2)

    # Step 2: Verify EvalManifest exists
    if not MANIFEST_PATH.exists():
        print(
            f"[ci_eval] ERROR: EvalManifest not found at {MANIFEST_PATH}. "
            "Run task 8.1 to generate the bootstrap manifest.",
            file=sys.stderr,
        )
        sys.exit(2)

    # Step 3: Run EvaluationPipeline
    print("[ci_eval] Loading manifest and running evaluation pipeline...")
    pipeline = EvaluationPipeline(api_key=api_key)
    manifest = pipeline.load_manifest()

    # Estimate time: ~5 sec/sample on free tier (12 req/min rate limiter)
    transcript_samples = [s for s in manifest.get("samples", []) if s["sample_type"] == "transcript"]
    image_samples = [s for s in manifest.get("samples", []) if s["sample_type"] != "transcript"]
    est_minutes = (len(transcript_samples) * 2 * 5 + len(image_samples) * 5) / 60
    print(f"[ci_eval] {len(manifest.get('samples',[]))} samples "
          f"({len(transcript_samples)} transcripts, {len(image_samples)} images)")
    print(f"[ci_eval] Estimated time: ~{est_minutes:.0f} minutes (Gemini free tier: 12 req/min)")
    print("[ci_eval] Running... (progress shown every 10 samples)")
    run_result = pipeline.run(manifest)

    # Step 4: Check thresholds
    failures = check_thresholds(run_result)

    # Step 5: Exit with appropriate code
    if failures:
        print("\n" + "=" * 70)
        print("  BHARAT KAVACH CI GATE — FAIL")
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
