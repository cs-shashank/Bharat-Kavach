"""
Property-based tests for the CIGate (ci_eval.py) — Phase 1.

Properties tested:
  12 — CIGate exits non-zero for any below-threshold metric combination
  13 — CIGate skips threshold check when sample_count < MIN_SAMPLES_FOR_GATE
"""

import os
import sys

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.eval_pipeline import (
    ComponentMetrics,
    EvalRunResult,
    MIN_SAMPLES_FOR_GATE,
    THRESHOLDS,
)

# Import the check_thresholds function from ci_eval
# We test the pure logic directly, not sys.exit behaviour
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ci_eval import check_thresholds

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_all_pass() -> EvalRunResult:
    """Build an EvalRunResult where every component meets or exceeds all thresholds."""
    run = EvalRunResult(
        run_id="test_pass",
        manifest_version=1,
        git_commit_sha="abc",
        run_at="2026-01-15T10:00:00Z",
    )
    run.per_component = {
        "BehavioralClassifier": ComponentMetrics(
            component="BehavioralClassifier",
            sample_count=MIN_SAMPLES_FOR_GATE,
            precision=0.90,
            recall=0.88,
            f1=0.89,
            fpr=0.05,
        ),
        "LegalRAG": ComponentMetrics(
            component="LegalRAG",
            sample_count=MIN_SAMPLES_FOR_GATE,
            precision=0.85,
            recall=0.80,
            f1=0.82,
            fpr=0.08,
        ),
        "VisionForensics": ComponentMetrics(
            component="VisionForensics",
            sample_count=MIN_SAMPLES_FOR_GATE,
            precision=0.80,
            recall=0.75,
            f1=0.77,
            fpr=0.10,
        ),
        "CurrencyVerifier": ComponentMetrics(
            component="CurrencyVerifier",
            sample_count=MIN_SAMPLES_FOR_GATE,
            precision=0.80,
            recall=0.75,
            f1=0.77,
            fpr=0.10,
        ),
    }
    return run


def _make_run_one_fail(component: str, bad_metric: str, bad_value: float) -> EvalRunResult:
    """Build an EvalRunResult where exactly one component has one metric below threshold."""
    run = _make_run_all_pass()
    m = run.per_component[component]
    setattr(m, bad_metric, bad_value)
    return run


# ---------------------------------------------------------------------------
# Property 12: CIGate exits non-zero for any below-threshold metric combination
# Feature: bharat-kavach-phase1, Property 12
# Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.6
# ---------------------------------------------------------------------------

# Generate (component, metric, bad_value) triples that should trigger failure
def _failing_cases_st():
    return st.one_of(
        # BehavioralClassifier precision below threshold
        st.tuples(
            st.just("BehavioralClassifier"),
            st.just("precision"),
            st.floats(min_value=0.0, max_value=0.849, allow_nan=False),
        ),
        # BehavioralClassifier FPR above threshold
        st.tuples(
            st.just("BehavioralClassifier"),
            st.just("fpr"),
            st.floats(min_value=0.101, max_value=1.0, allow_nan=False),
        ),
        # LegalRAG precision below threshold
        st.tuples(
            st.just("LegalRAG"),
            st.just("precision"),
            st.floats(min_value=0.0, max_value=0.799, allow_nan=False),
        ),
        # VisionForensics precision below threshold
        st.tuples(
            st.just("VisionForensics"),
            st.just("precision"),
            st.floats(min_value=0.0, max_value=0.749, allow_nan=False),
        ),
        # CurrencyVerifier precision below threshold
        st.tuples(
            st.just("CurrencyVerifier"),
            st.just("precision"),
            st.floats(min_value=0.0, max_value=0.749, allow_nan=False),
        ),
    )


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(_failing_cases_st())
def test_property_12_below_threshold_returns_failures(case):
    # Feature: bharat-kavach-phase1, Property 12: CIGate exits non-zero for any below-threshold metric combination
    component, metric, bad_value = case
    run = _make_run_one_fail(component, metric, bad_value)
    failures = check_thresholds(run)
    assert len(failures) > 0, (
        f"Expected at least one failure when {component}.{metric}={bad_value:.3f}, "
        f"but check_thresholds returned empty list"
    )


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(st.just(None))  # parametrised with a dummy to keep the @given pattern
def test_property_12_all_passing_returns_no_failures(_):
    # Feature: bharat-kavach-phase1, Property 12 (passing case): all metrics at or above threshold → no failures
    run = _make_run_all_pass()
    failures = check_thresholds(run)
    assert failures == [], (
        f"Expected no failures for all-passing run, got: {failures}"
    )


# ---------------------------------------------------------------------------
# Property 13: CIGate skips threshold check when sample_count < MIN_SAMPLES_FOR_GATE
# Feature: bharat-kavach-phase1, Property 13
# Validates: Requirements 9.8
# ---------------------------------------------------------------------------

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.sampled_from(list(THRESHOLDS.keys())),
    st.integers(min_value=0, max_value=MIN_SAMPLES_FOR_GATE - 1),
)
def test_property_13_insufficient_data_skips_gate(component, sample_count):
    # Feature: bharat-kavach-phase1, Property 13: CIGate skips threshold check when sample_count < MIN_SAMPLES_FOR_GATE
    run = _make_run_all_pass()
    # Set the sample_count to below the minimum — and set precision to 0 to ensure
    # it would fail if the gate ran
    m = run.per_component[component]
    m.sample_count = sample_count
    m.precision = 0.0  # would fail every threshold if evaluated

    failures = check_thresholds(run)

    # The component with insufficient data must not appear in failures
    component_failures = [f for f in failures if component in f]
    assert len(component_failures) == 0, (
        f"Component {component} with sample_count={sample_count} should be skipped "
        f"(< MIN_SAMPLES_FOR_GATE={MIN_SAMPLES_FOR_GATE}), "
        f"but produced failures: {component_failures}"
    )
