"""
Property-based tests for EvidenceExporter — Bharat Kavach Phase 1.

Properties tested:
  1  — Bundle SHA-256 integrity is self-consistent
  2  — Bundle structure invariant: all four components always present
  3  — Bundle hash invalidation on mutation
  4  — JSON export round-trip preserves all bundle fields
  5  — Exported filename always matches naming convention
  6  — Partial export survives component serialisation failure
  7  — PDF contains all required content sections

All properties run with @settings(max_examples=100).

NOTE: @given tests cannot use pytest tmp_path fixture — they create their own
temp directories via tempfile.mkdtemp() and clean up via shutil.rmtree().
"""

import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evidence_exporter import (
    COMPONENT_NAMES,
    ChainOfCustodyEntry,
    ComponentVerdict,
    EvidenceBundle,
    EvidenceExporter,
    JsonWriteError,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _not_applicable_verdicts():
    return {n: ComponentVerdict(verdict="not_applicable") for n in COMPONENT_NAMES}


def _make_exporter_in(tmpdir: str) -> EvidenceExporter:
    exp = EvidenceExporter()
    exp.EXPORTS_DIR = Path(tmpdir) / "exports"
    exp.FAILURE_LOG = Path(tmpdir) / "logs" / "failures.log"
    exp.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return exp


def _minimal_bundle(**overrides) -> EvidenceBundle:
    defaults = dict(
        analyzed_at="2026-01-15T10:30:00Z",
        case_id=1,
        sha256_hash="",
        model_registry={n: "test-model" for n in COMPONENT_NAMES},
        chain_of_custody=[],
        component_verdicts=_not_applicable_verdicts(),
    )
    defaults.update(overrides)
    bundle = EvidenceBundle(**defaults)
    bundle.sha256_hash = EvidenceExporter().compute_hash(bundle)
    return bundle


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_verdict_st = st.builds(
    ComponentVerdict,
    verdict=st.text(min_size=1, max_size=40),
    confidence=st.one_of(
        st.none(),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    ),
    details=st.one_of(st.none(), st.just({"k": "v"})),
)

_bundle_st = st.builds(
    EvidenceBundle,
    bundle_id=st.uuids().map(str),
    analyzed_at=st.just("2026-01-15T10:30:00Z"),
    case_id=st.integers(min_value=1, max_value=99999),
    sha256_hash=st.just(""),
    model_registry=st.just({n: "m" for n in COMPONENT_NAMES}),
    chain_of_custody=st.just([]),
    component_verdicts=st.fixed_dictionaries({n: _verdict_st for n in COMPONENT_NAMES}),
)


# ---------------------------------------------------------------------------
# Property 1: Bundle SHA-256 integrity is self-consistent
# Feature: bharat-kavach-phase1, Property 1: Bundle SHA-256 integrity is self-consistent
# Validates: Requirements 1.3, 1.8
# ---------------------------------------------------------------------------

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(_bundle_st)
def test_property_1_hash_self_consistent(bundle: EvidenceBundle):
    # Feature: bharat-kavach-phase1, Property 1: Bundle SHA-256 integrity is self-consistent
    exporter = EvidenceExporter()
    computed = exporter.compute_hash(bundle)
    bundle.sha256_hash = computed
    assert exporter.verify_hash(bundle), (
        f"verify_hash returned False immediately after setting sha256_hash=compute_hash. "
        f"bundle_id={bundle.bundle_id}"
    )


# ---------------------------------------------------------------------------
# Property 2: Bundle structure invariant — all four components always present
# Feature: bharat-kavach-phase1, Property 2
# Validates: Requirements 1.4, 1.6, 1.7
# ---------------------------------------------------------------------------

_partial_verdicts_st = st.fixed_dictionaries({
    name: st.one_of(
        _verdict_st,
        st.just(ComponentVerdict(verdict="not_applicable", confidence=None, details=None)),
    )
    for name in COMPONENT_NAMES
})

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    st.builds(
        EvidenceBundle,
        bundle_id=st.uuids().map(str),
        analyzed_at=st.just("2026-01-15T10:30:00Z"),
        case_id=st.integers(min_value=1),
        sha256_hash=st.just(""),
        model_registry=st.just({n: "m" for n in COMPONENT_NAMES}),
        chain_of_custody=st.just([]),
        component_verdicts=_partial_verdicts_st,
    )
)
def test_property_2_all_four_components_present(bundle: EvidenceBundle):
    # Feature: bharat-kavach-phase1, Property 2: Bundle structure invariant — all four components always present
    assert set(bundle.component_verdicts.keys()) == set(COMPONENT_NAMES), (
        f"Missing components: {set(COMPONENT_NAMES) - set(bundle.component_verdicts.keys())}"
    )
    for name in COMPONENT_NAMES:
        cv = bundle.component_verdicts[name]
        assert cv.verdict is not None, f"{name}.verdict must not be None"


# ---------------------------------------------------------------------------
# Property 3: Bundle hash invalidation on mutation
# Feature: bharat-kavach-phase1, Property 3
# Validates: Requirements 1.8
# ---------------------------------------------------------------------------

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    _bundle_st,
    st.sampled_from(["case_id", "analyzed_at"]),
)
def test_property_3_hash_invalidated_on_mutation(bundle: EvidenceBundle, field: str):
    # Feature: bharat-kavach-phase1, Property 3: Bundle hash invalidation on mutation
    exporter = EvidenceExporter()
    bundle.sha256_hash = exporter.compute_hash(bundle)
    assert exporter.verify_hash(bundle), "Pre-condition: bundle should verify before mutation"

    if field == "case_id":
        bundle.case_id = bundle.case_id + 1
    elif field == "analyzed_at":
        bundle.analyzed_at = "1999-01-01T00:00:00Z"

    assert not exporter.verify_hash(bundle), (
        f"verify_hash returned True after mutating {field} — hash was NOT invalidated"
    )


# ---------------------------------------------------------------------------
# Property 4: JSON export round-trip preserves all bundle fields
# Feature: bharat-kavach-phase1, Property 4
# Validates: Requirements 2.1, 2.2, 2.3
# ---------------------------------------------------------------------------

@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(_bundle_st)
def test_property_4_json_round_trip(bundle: EvidenceBundle):
    # Feature: bharat-kavach-phase1, Property 4: JSON export round-trip preserves all bundle fields
    tmpdir = tempfile.mkdtemp(prefix="bk_test_p4_")
    try:
        exporter = _make_exporter_in(tmpdir)
        bundle.sha256_hash = exporter.compute_hash(bundle)

        path = exporter.export_json(bundle)
        assert path.exists(), "export_json must create a file"

        data = json.loads(path.read_text(encoding="utf-8"))

        assert data["bundle_id"] == bundle.bundle_id
        assert data["case_id"] == bundle.case_id
        assert data["analyzed_at"] == bundle.analyzed_at
        assert data["sha256_hash"] == bundle.sha256_hash

        for name in COMPONENT_NAMES:
            assert name in data["component_verdicts"], f"{name} missing from round-tripped JSON"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Property 5: Exported filename always matches naming convention
# Feature: bharat-kavach-phase1, Property 5
# Validates: Requirements 2.4, 3.1
# ---------------------------------------------------------------------------

@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(st.uuids().map(str))
def test_property_5_filename_convention(bid: str):
    # Feature: bharat-kavach-phase1, Property 5: Exported filename always matches naming convention
    tmpdir = tempfile.mkdtemp(prefix="bk_test_p5_")
    try:
        exporter = _make_exporter_in(tmpdir)
        bundle = _minimal_bundle(bundle_id=bid)

        json_path = exporter.export_json(bundle)
        assert json_path.name == f"BK-{bid}.evidence.json", (
            f"Expected BK-{bid}.evidence.json, got {json_path.name}"
        )

        pdf_expected = exporter.get_pdf_path(bid)
        assert pdf_expected.name == f"BK-{bid}.summary.pdf", (
            f"Expected BK-{bid}.summary.pdf, got {pdf_expected.name}"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Property 6: Partial export survives component serialisation failure
# Feature: bharat-kavach-phase1, Property 6
# Validates: Requirements 2.5
# ---------------------------------------------------------------------------

@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
@given(st.sampled_from(COMPONENT_NAMES))
def test_property_6_partial_export_on_serialisation_failure(bad_component: str):
    # Feature: bharat-kavach-phase1, Property 6: Partial export survives component serialisation failure
    tmpdir = tempfile.mkdtemp(prefix="bk_test_p6_")
    try:
        exporter = _make_exporter_in(tmpdir)
        bundle = _minimal_bundle()

        # Inject a raw unserializable sentinel directly into the internal __dict__
        # bypassing Pydantic's validation. We patch export_json's per-component
        # serialisation by replacing the component_verdicts dict with a subclass
        # that raises on the targeted key's model_dump.
        class _BrokenVerdict:
            """A non-Pydantic object that mimics ComponentVerdict but raises on model_dump."""
            verdict = "broken"
            confidence = None
            details = None

            def model_dump(self, **kwargs):
                raise TypeError("Intentionally unserializable for test")

        # Replace the component_verdicts dict entry with the broken object
        bundle.component_verdicts[bad_component] = _BrokenVerdict()  # type: ignore[assignment]

        # Must NOT raise — should produce a partial export
        path = exporter.export_json(bundle)

        # (a) A file is still produced
        assert path.exists(), "Partial export file should still be created"

        data = json.loads(path.read_text(encoding="utf-8"))

        # (b) chain_of_custody contains a serialisation_error entry
        coc_actions = [e["action"] for e in data.get("chain_of_custody", [])]
        assert any("serialisation_error" in a for a in coc_actions), (
            f"Expected serialisation_error in chain_of_custody, got: {coc_actions}"
        )

        # (c) Other components' verdicts are intact
        for name in COMPONENT_NAMES:
            if name != bad_component:
                assert name in data["component_verdicts"], (
                    f"{name} should be present in partial export"
                )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Property 7: PDF contains all required content sections
# Feature: bharat-kavach-phase1, Property 7
# Validates: Requirements 3.2, 3.3, 3.4, 3.5
# ---------------------------------------------------------------------------

@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(_bundle_st)
def test_property_7_pdf_required_content(bundle: EvidenceBundle):
    # Feature: bharat-kavach-phase1, Property 7: PDF contains all required content sections
    try:
        from pdfminer.high_level import extract_text as pdf_extract
    except ImportError:
        pytest.skip("pdfminer.six not installed — pip install pdfminer.six")

    tmpdir = tempfile.mkdtemp(prefix="bk_test_p7_")
    try:
        exporter = _make_exporter_in(tmpdir)
        bundle.sha256_hash = exporter.compute_hash(bundle)

        pdf_path = exporter.export_pdf(bundle)
        assert pdf_path.exists(), "export_pdf must create a file"

        text = pdf_extract(str(pdf_path))

        assert bundle.bundle_id in text, f"PDF must contain bundle_id {bundle.bundle_id!r}"
        assert str(bundle.case_id) in text, f"PDF must contain case_id {bundle.case_id}"
        for name in COMPONENT_NAMES:
            assert name in text, f"PDF must contain component name: {name}"
        assert "automated forensic estimate" in text.lower(), (
            "PDF must contain disclaimer phrase 'automated forensic estimate'"
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Example tests
# ---------------------------------------------------------------------------

def test_verify_hash_returns_false_for_empty_hash():
    """verify_hash returns False when sha256_hash is empty."""
    exporter = EvidenceExporter()
    bundle = _minimal_bundle()
    bundle.sha256_hash = ""
    assert not exporter.verify_hash(bundle)


def test_fallback_log_written_on_write_failure(tmp_path):
    """When the primary JSON write is patched to fail, the fallback log is written."""
    exporter = _make_exporter_in(str(tmp_path))

    bundle = _minimal_bundle()

    # Patch Path.write_text to simulate a disk write failure
    original_write_text = Path.write_text

    def fail_write(self, *args, **kwargs):
        if "evidence.json" in str(self):
            raise OSError("Simulated disk full")
        return original_write_text(self, *args, **kwargs)

    with patch.object(Path, "write_text", fail_write):
        with pytest.raises(JsonWriteError):
            exporter.export_json(bundle)

    assert exporter.FAILURE_LOG.exists(), "Fallback failure log must be created on write error"
    content = exporter.FAILURE_LOG.read_text()
    assert "FAILURE" in content
    assert bundle.bundle_id in content
