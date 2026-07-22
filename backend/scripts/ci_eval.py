"""
ci_eval.py — Shared CI gate logic used by ci_eval_fast.py and test_ci_gate.py.

Contains check_thresholds() and print_pass_summary() — the pure threshold
checking functions that don't require API keys or file I/O.
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from services.eval_pipeline import (
    EvalRunResult,
    THRESHOLDS,
    MIN_SAMPLES_FOR_GATE,
)


def check_thresholds(run_result: EvalRunResult) -> list:
    """
    Compare per-component metrics against THRESHOLDS.
    Returns a list of failure message strings (empty list = all pass).
    Components with sample_count < MIN_SAMPLES_FOR_GATE are skipped.
    """
    failures = []

    for component, thresholds in THRESHOLDS.items():
        metrics = run_result.per_component.get(component)
        if metrics is None:
            continue

        if metrics.sample_count < MIN_SAMPLES_FOR_GATE:
            print(
                f"  WARNING: insufficient data for {component} "
                f"(n={metrics.sample_count} < {MIN_SAMPLES_FOR_GATE}); "
                f"skipping gate"
            )
            continue

        # Precision check (all components)
        min_precision = thresholds.get("precision")
        if min_precision is not None and metrics.precision < min_precision:
            failures.append(
                f"  FAIL {component}: precision={metrics.precision:.3f} "
                f"< threshold {min_precision}"
            )

        # FPR check (BehavioralClassifier only)
        max_fpr = thresholds.get("fpr")
        if max_fpr is not None and metrics.fpr > max_fpr:
            failures.append(
                f"  FAIL {component}: fpr={metrics.fpr:.3f} "
                f"> threshold {max_fpr}"
            )

    return failures


def print_pass_summary(run_result: EvalRunResult):
    """Print a formatted PASS summary table to stdout."""
    print("\n" + "=" * 70)
    print("  BHARAT KAVACH CI GATE — PASS")
    print("=" * 70)
    print(f"  {'Component':<25} {'Precision':>10} {'FPR':>8}  Threshold")
    print("-" * 70)

    for component, thresholds in THRESHOLDS.items():
        metrics = run_result.per_component.get(component)
        if metrics is None or metrics.sample_count < MIN_SAMPLES_FOR_GATE:
            print(f"  {component:<25} {'—':>10} {'—':>8}  SKIPPED (insufficient data)")
            continue

        precision_str = f"{metrics.precision:.3f}"
        fpr_str = f"{metrics.fpr:.3f}" if thresholds.get("fpr") else "—"

        t_str = f"P≥{thresholds['precision']}"
        if thresholds.get("fpr"):
            t_str += f" / FPR≤{thresholds['fpr']}"

        print(f"  {component:<25} {precision_str:>10} {fpr_str:>8}  {t_str}  ✓")

    print("=" * 70)
    print(f"  Run ID: {run_result.run_id}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("ci_eval.py: shared CI gate logic module. Use ci_eval_fast.py to run the full gate.")
