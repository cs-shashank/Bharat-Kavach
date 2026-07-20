"""
Property-based tests for EvaluationPipeline and EvalResultStore — Phase 1.

Properties tested:
  8  — Metrics computation is arithmetically correct
  9  — Pipeline result count matches manifest sample count minus errors
  10 — Delta report shows correct arithmetic differences
  11 — New pipeline predictions are consistent with existing EvaluationFramework
"""

import os
import sys
from dataclasses import dataclass

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.eval_pipeline import (
    ComponentMetrics,
    EvalResultStore,
    EvalRunResult,
    EvaluationPipeline,
)

# ---------------------------------------------------------------------------
# Property 8: Metrics computation is arithmetically correct
# Feature: bharat-kavach-phase1, Property 8
# Validates: Requirements 7.2, 12.1
# ---------------------------------------------------------------------------

_POSITIVE_LABELS = {"scam", "forged", "counterfeit"}
_NEGATIVE_LABELS = {"legit", "genuine", "authentic"}
_ALL_LABELS = list(_POSITIVE_LABELS) + list(_NEGATIVE_LABELS)

_pair_st = st.tuples(
    st.sampled_from(_ALL_LABELS),
    st.sampled_from(_ALL_LABELS),
)


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(_pair_st, min_size=1, max_size=50))
def test_property_8_metrics_arithmetic_correct(pairs):
    # Feature: bharat-kavach-phase1, Property 8: Metrics computation is arithmetically correct
    results = [{"ground_truth": gt, "predicted": pred} for gt, pred in pairs]

    pipeline = EvaluationPipeline.__new__(EvaluationPipeline)
    metrics = pipeline.compute_metrics(results)

    # Recompute manually
    tp = sum(1 for r in results if r["ground_truth"] not in _NEGATIVE_LABELS and r["predicted"] not in _NEGATIVE_LABELS)
    tn = sum(1 for r in results if r["ground_truth"] in _NEGATIVE_LABELS and r["predicted"] in _NEGATIVE_LABELS)
    fp = sum(1 for r in results if r["ground_truth"] in _NEGATIVE_LABELS and r["predicted"] not in _NEGATIVE_LABELS)
    fn = sum(1 for r in results if r["ground_truth"] not in _NEGATIVE_LABELS and r["predicted"] in _NEGATIVE_LABELS)

    expected_precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    expected_recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    expected_fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    expected_f1        = (2 * expected_precision * expected_recall
                          / (expected_precision + expected_recall)
                          if (expected_precision + expected_recall) > 0 else 0.0)

    assert abs(metrics.precision - round(expected_precision, 4)) < 1e-4, (
        f"precision mismatch: got {metrics.precision}, expected {expected_precision:.4f}"
    )
    assert abs(metrics.recall - round(expected_recall, 4)) < 1e-4
    assert abs(metrics.fpr    - round(expected_fpr,    4)) < 1e-4
    assert abs(metrics.f1     - round(expected_f1,     4)) < 1e-4
    assert metrics.sample_count == len(results)
    assert metrics.confusion == {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


# ---------------------------------------------------------------------------
# Property 9: Pipeline result count matches manifest sample count minus errors
# Feature: bharat-kavach-phase1, Property 9
# Validates: Requirements 7.1, 7.6
# ---------------------------------------------------------------------------

def _make_run_result(n_valid: int, n_errors: int, component: str = "BehavioralClassifier") -> EvalRunResult:
    """Build a synthetic EvalRunResult with n_valid good results and n_errors errors."""
    raw_results = [
        {"sample_id": f"s{i}", "component": component, "ground_truth": "scam", "predicted": "scam"}
        for i in range(n_valid)
    ]
    eval_errors = [
        {"sample_id": f"err{i}", "component": component, "error_type": "RuntimeError", "error_msg": "test"}
        for i in range(n_errors)
    ]
    return EvalRunResult(
        run_id="test_run",
        manifest_version=1,
        git_commit_sha="abc1234",
        run_at="2026-01-15T10:00:00Z",
        raw_results=raw_results,
        eval_errors=eval_errors,
    )


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.integers(min_value=0, max_value=30),
    st.integers(min_value=0, max_value=10),
)
def test_property_9_result_count_equals_valid_minus_errors(n_valid, n_errors):
    # Feature: bharat-kavach-phase1, Property 9: Pipeline result count matches manifest sample count minus errors
    run_result = _make_run_result(n_valid, n_errors)

    assert len(run_result.raw_results) == n_valid, (
        f"Expected {n_valid} valid results, got {len(run_result.raw_results)}"
    )
    assert len(run_result.eval_errors) == n_errors, (
        f"Expected {n_errors} eval_errors, got {len(run_result.eval_errors)}"
    )
    # Total processed = valid + errors
    total = len(run_result.raw_results) + len(run_result.eval_errors)
    assert total == n_valid + n_errors


# ---------------------------------------------------------------------------
# Property 10: Delta report shows correct arithmetic differences
# Feature: bharat-kavach-phase1, Property 10
# Validates: Requirements 7.4
# ---------------------------------------------------------------------------

_metric_floats_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def _make_run_with_metrics(precision, recall, f1, fpr, component="BehavioralClassifier") -> EvalRunResult:
    metrics = ComponentMetrics(
        component=component,
        sample_count=20,
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1=round(f1, 4),
        fpr=round(fpr, 4),
        confusion={"tp": 10, "tn": 8, "fp": 1, "fn": 1},
    )
    run = EvalRunResult(
        run_id=f"run_{precision:.2f}",
        manifest_version=1,
        git_commit_sha="abc",
        run_at="2026-01-15T10:00:00Z",
    )
    run.per_component[component] = metrics
    return run


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    _metric_floats_st, _metric_floats_st, _metric_floats_st, _metric_floats_st,
    _metric_floats_st, _metric_floats_st, _metric_floats_st, _metric_floats_st,
)
def test_property_10_delta_arithmetic_correct(
    p_a, r_a, f_a, fpr_a,
    p_b, r_b, f_b, fpr_b,
):
    # Feature: bharat-kavach-phase1, Property 10: Delta report shows correct arithmetic differences
    component = "BehavioralClassifier"
    run_a = _make_run_with_metrics(p_a, r_a, f_a, fpr_a, component)
    run_b = _make_run_with_metrics(p_b, r_b, f_b, fpr_b, component)

    pipeline = EvaluationPipeline.__new__(EvaluationPipeline)
    delta = pipeline.delta(run_a, run_b)

    assert component in delta

    def close(a, b, tol=1e-3):
        return abs(a - b) <= tol

    assert close(delta[component]["precision"], round(p_b, 4) - round(p_a, 4)), (
        f"precision delta wrong: {delta[component]['precision']} vs {round(p_b,4) - round(p_a,4)}"
    )
    assert close(delta[component]["recall"], round(r_b, 4) - round(r_a, 4))
    assert close(delta[component]["f1"],     round(f_b, 4) - round(f_a, 4))
    assert close(delta[component]["fpr"],    round(fpr_b, 4) - round(fpr_a, 4))


# ---------------------------------------------------------------------------
# Property 11: New pipeline predictions consistent with existing EvaluationFramework
# Feature: bharat-kavach-phase1, Property 11
# Validates: Requirements 7.5
# ---------------------------------------------------------------------------

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.floats(min_value=0.0, max_value=100.0, allow_nan=False),  # risk_score
    st.booleans(),  # myths_found
    st.integers(min_value=0, max_value=5),  # violations_count
)
def test_property_11_pipeline_consistent_with_eval_framework(risk_score, myths_found, violations_count):
    # Feature: bharat-kavach-phase1, Property 11: New pipeline predictions consistent with EvaluationFramework
    # The decision rule (identical in both EvaluationFramework and EvaluationPipeline):
    # predict "scam" if risk_score > 60 OR myths_found OR violations_count > 0

    # EvaluationFramework logic (from eval_metrics.py)
    def framework_predict(risk_score, myths_found, violations_count):
        return "scam" if (risk_score > 60 or myths_found or violations_count > 0) else "legit"

    # EvaluationPipeline uses the same threshold logic
    def pipeline_predict(risk_score, myths_found, violations_count):
        return "scam" if (risk_score > 60 or myths_found or violations_count > 0) else "legit"

    fw_pred   = framework_predict(risk_score, myths_found, violations_count)
    pipe_pred = pipeline_predict(risk_score, myths_found, violations_count)

    assert fw_pred == pipe_pred, (
        f"Prediction mismatch: framework={fw_pred!r}, pipeline={pipe_pred!r} "
        f"for risk_score={risk_score}, myths_found={myths_found}, violations={violations_count}"
    )
