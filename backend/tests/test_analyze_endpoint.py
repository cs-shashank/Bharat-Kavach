"""
Property-based tests for the /analyze endpoint.

Property 6: Kill-switch fires iff both threshold conditions are met
  Validates: Requirements 5.1, 5.6
"""

# Feature: bharat-kavach-complete, Property 6: Kill-switch fires iff both threshold conditions are met

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out heavy / unavailable native modules BEFORE any app code is imported.
# cv2 (OpenCV) and whisper_timestamped are not installed in this test env.
# ---------------------------------------------------------------------------
for _mod in ("cv2", "whisper_timestamped", "whisper"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hypothesis import given, settings, HealthCheck
import hypothesis.strategies as st

KILL_SWITCH_STAGE = "Financial Demand / UPI Request"


# ---------------------------------------------------------------------------
# Property 6: Kill-switch fires iff both threshold conditions are met
#
# We call the analyze_call coroutine directly (bypassing HTTP) to avoid the
# per-example overhead of spinning up a full ASGI event-loop in TestClient.
# This still exercises the real branching logic in main.py.
# ---------------------------------------------------------------------------

@settings(
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
@given(
    confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    stage=st.text(min_size=0, max_size=200),
)
def test_kill_switch_fires_iff_both_conditions_met(confidence, stage):
    """
    # Feature: bharat-kavach-complete, Property 6: Kill-switch fires iff both threshold conditions are met
    Validates: Requirements 5.1, 5.6

    For any confidence in [0, 1] and any stage string:
      trigger_kill_switch is called exactly once  iff  confidence * 100 > 85  AND  stage == KILL_SWITCH_STAGE
      trigger_kill_switch is NOT called            otherwise
    """
    from ai_engines.behavioral import AnalysisResult
    from database import Base, CaseReport
    import main as app_module
    from main import TranscriptRequest, analyze_call

    # In-memory SQLite DB for this test
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestSession()

    # Build fake AnalysisResult with the Hypothesis-generated values
    fake_analysis = AnalysisResult(
        current_stage=stage,
        confidence=confidence,
        reasoning="property test stub",
        red_flags=[],
        intervention_required=False,
    )

    mock_classifier = MagicMock()
    mock_classifier.analyze_transcript.return_value = fake_analysis

    mock_legal_rag = MagicMock()
    mock_legal_rag.verify_legal_claims.return_value = []

    mock_ks = MagicMock(return_value={
        "success": True,
        "actions_taken": ["UPI_HOLD"],
        "incident_id": "BK-TEST-001",
    })

    mock_broadcast = AsyncMock()

    request = TranscriptRequest(transcript="test transcript", user_id="TEST_USER")

    try:
        with patch.object(app_module, "classifier", mock_classifier), \
             patch.object(app_module, "legal_rag", mock_legal_rag), \
             patch.object(app_module, "MOCK_MODE", False), \
             patch("services.intervention.InterventionService.trigger_kill_switch", mock_ks), \
             patch.object(app_module.manager, "broadcast", mock_broadcast):

            result = asyncio.run(analyze_call(request, db))

        should_fire = (confidence * 100 > 85) and (stage == KILL_SWITCH_STAGE)

        if should_fire:
            assert mock_ks.call_count == 1, (
                f"Expected trigger_kill_switch called once for confidence={confidence}, "
                f"stage={stage!r}, but call_count={mock_ks.call_count}"
            )
            assert result.get("intervention_triggered") is True, (
                f"Expected intervention_triggered=True in result, got: {result}"
            )
        else:
            assert mock_ks.call_count == 0, (
                f"Expected trigger_kill_switch NOT called for confidence={confidence}, "
                f"stage={stage!r}, but call_count={mock_ks.call_count}"
            )
            assert result.get("intervention_triggered") is False, (
                f"Expected intervention_triggered=False in result, got: {result}"
            )

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Property 7: Intervention data persists to DB and appears in HTTP response
#
# Feature: bharat-kavach-complete, Property 7: Intervention data persists to DB
# and appears in HTTP response
# Validates: Requirements 5.2, 5.3, 5.6, 5.7
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Shared helpers for the three example tests below
# ---------------------------------------------------------------------------

def _make_engine_and_client():
    """
    Build an isolated in-memory SQLite DB using StaticPool so that all
    SQLAlchemy connections share the same in-memory DB instance.
    Patches database module globals and the FastAPI dependency override,
    and returns (engine, TestClient, session_factory).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    import database as db_module
    from database import Base, get_db
    import main as app_module
    from fastapi.testclient import TestClient

    # StaticPool ensures every connection reuses the same underlying SQLite
    # in-memory connection, so tables created by create_all are visible to
    # subsequent sessions/transactions.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Patch the module-level engine and SessionLocal so any code that
    # accesses database.engine or database.SessionLocal gets the test DB.
    db_module.engine = engine
    db_module.SessionLocal = TestSession

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app_module.app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app_module.app)
    return engine, client, TestSession


# ---------------------------------------------------------------------------
# Example test 1
# POST /analyze with confidence=0.90 and stage="Financial Demand / UPI Request"
# → HTTP 200 with intervention_triggered: true and non-empty intervention_result
# → CaseReport in DB has non-empty interventions list
# ---------------------------------------------------------------------------

def test_intervention_triggered_persists_to_db_and_response():
    """
    Property 7 — Example 1
    Validates: Requirements 5.2, 5.3

    When BehavioralClassifier returns confidence=0.90 and stage
    "Financial Demand / UPI Request", the endpoint must:
      • respond with intervention_triggered=true and a non-empty intervention_result
      • persist the actions_taken list to CaseReport.interventions in the DB
    """
    from ai_engines.behavioral import AnalysisResult
    from database import CaseReport
    import main as app_module

    engine, client, TestSession = _make_engine_and_client()

    fake_analysis = AnalysisResult(
        current_stage="Financial Demand / UPI Request",
        confidence=0.90,
        reasoning="test stub",
        red_flags=["UPI requested"],
        intervention_required=True,
    )

    mock_classifier = MagicMock()
    mock_classifier.analyze_transcript.return_value = fake_analysis

    mock_legal_rag = MagicMock()
    mock_legal_rag.verify_legal_claims.return_value = []

    mock_ks_result = {
        "success": True,
        "actions_taken": ["UPI_HOLD", "TELECOM_FLAG", "POLICE_ALERT"],
        "incident_id": "BK-TEST-P7-001",
    }
    mock_ks = MagicMock(return_value=mock_ks_result)

    try:
        with patch.object(app_module, "classifier", mock_classifier), \
             patch.object(app_module, "legal_rag", mock_legal_rag), \
             patch.object(app_module, "MOCK_MODE", False), \
             patch("services.intervention.InterventionService.trigger_kill_switch", mock_ks):

            response = client.post(
                "/analyze",
                json={"transcript": "Please transfer ₹50,000 via UPI immediately.", "user_id": "TEST_USER_P7"},
            )

        # --- HTTP response assertions ---
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        body = response.json()
        assert body.get("intervention_triggered") is True, (
            f"Expected intervention_triggered=True in response, got: {body}"
        )
        assert "intervention_result" in body, (
            f"Expected 'intervention_result' key in response, got: {body}"
        )
        assert body["intervention_result"], (
            f"Expected non-empty intervention_result, got: {body['intervention_result']}"
        )

        # --- DB persistence assertions ---
        db = TestSession()
        try:
            case_in_db = db.query(CaseReport).filter_by(user_id="TEST_USER_P7").first()
            assert case_in_db is not None, "Expected CaseReport to be saved to DB"
            assert case_in_db.interventions, (
                f"Expected non-empty interventions in DB record, got: {case_in_db.interventions}"
            )
        finally:
            db.close()

    finally:
        app_module.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Example test 2
# POST /analyze with confidence=0.90 but stage="Authority Impersonation"
# (high confidence but WRONG stage) → intervention_triggered must be false
# → trigger_kill_switch must NOT be called
# ---------------------------------------------------------------------------

def test_intervention_not_triggered_for_wrong_stage():
    """
    Property 7 — Example 2
    Validates: Requirements 5.6

    When confidence is high (0.90) but stage is NOT
    "Financial Demand / UPI Request", the endpoint must:
      • respond with intervention_triggered=false
      • NOT call trigger_kill_switch at all
      • NOT include intervention_result in the response
    """
    from ai_engines.behavioral import AnalysisResult
    import main as app_module

    engine, client, TestSession = _make_engine_and_client()

    fake_analysis = AnalysisResult(
        current_stage="Authority Impersonation",
        confidence=0.90,
        reasoning="test stub",
        red_flags=["police claim"],
        intervention_required=False,
    )

    mock_classifier = MagicMock()
    mock_classifier.analyze_transcript.return_value = fake_analysis

    mock_legal_rag = MagicMock()
    mock_legal_rag.verify_legal_claims.return_value = []

    mock_ks = MagicMock()

    try:
        with patch.object(app_module, "classifier", mock_classifier), \
             patch.object(app_module, "legal_rag", mock_legal_rag), \
             patch.object(app_module, "MOCK_MODE", False), \
             patch("services.intervention.InterventionService.trigger_kill_switch", mock_ks):

            response = client.post(
                "/analyze",
                json={
                    "transcript": "I am officer from CBI, you are under digital arrest.",
                    "user_id": "TEST_USER_P7_STAGE",
                },
            )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        body = response.json()

        assert body.get("intervention_triggered") is False, (
            f"Expected intervention_triggered=False, got: {body}"
        )
        assert "intervention_result" not in body, (
            f"intervention_result should be absent from response when not triggered, got: {body}"
        )
        assert mock_ks.call_count == 0, (
            f"trigger_kill_switch should NOT have been called, but call_count={mock_ks.call_count}"
        )

    finally:
        app_module.app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Example test 3
# POST /analyze when InterventionService raises an exception
# → HTTP 200 with intervention_triggered: false and intervention_error key present
# → CaseReport still saved to DB with empty interventions list
# ---------------------------------------------------------------------------

def test_intervention_service_raises_returns_error_in_response():
    """
    Property 7 — Example 3
    Validates: Requirements 5.7

    When InterventionService.trigger_kill_switch raises an exception on a
    qualifying high-risk transcript, the endpoint must:
      • still return HTTP 200 (graceful degradation)
      • include intervention_triggered=false
      • include an 'intervention_error' key in the response
      • save the CaseReport to DB with an empty interventions list
    """
    from ai_engines.behavioral import AnalysisResult
    from database import CaseReport
    import main as app_module

    engine, client, TestSession = _make_engine_and_client()

    fake_analysis = AnalysisResult(
        current_stage="Financial Demand / UPI Request",
        confidence=0.90,
        reasoning="test stub",
        red_flags=["UPI requested"],
        intervention_required=True,
    )

    mock_classifier = MagicMock()
    mock_classifier.analyze_transcript.return_value = fake_analysis

    mock_legal_rag = MagicMock()
    mock_legal_rag.verify_legal_claims.return_value = []

    # Simulate a downstream failure in the kill-switch service
    mock_ks = MagicMock(side_effect=RuntimeError("Bank API unreachable"))

    try:
        with patch.object(app_module, "classifier", mock_classifier), \
             patch.object(app_module, "legal_rag", mock_legal_rag), \
             patch.object(app_module, "MOCK_MODE", False), \
             patch("services.intervention.InterventionService.trigger_kill_switch", mock_ks):

            response = client.post(
                "/analyze",
                json={
                    "transcript": "Transfer ₹1,00,000 UPI to clear your account.",
                    "user_id": "TEST_USER_P7_ERR",
                },
            )

        assert response.status_code == 200, (
            f"Expected HTTP 200 even on intervention failure, got {response.status_code}: {response.text}"
        )
        body = response.json()

        assert body.get("intervention_triggered") is False, (
            f"Expected intervention_triggered=False on service error, got: {body}"
        )
        assert "intervention_error" in body, (
            f"Expected 'intervention_error' key in response on failure, got: {body}"
        )
        assert body["intervention_error"], (
            f"Expected non-empty intervention_error string, got: {body['intervention_error']}"
        )

        # DB record must still be saved, but with empty interventions
        db = TestSession()
        try:
            case_in_db = db.query(CaseReport).filter_by(user_id="TEST_USER_P7_ERR").first()
            assert case_in_db is not None, "Expected CaseReport to be saved to DB even on intervention error"
            assert case_in_db.interventions == [] or case_in_db.interventions is None, (
                f"Expected empty interventions list in DB on error, got: {case_in_db.interventions}"
            )
        finally:
            db.close()

    finally:
        app_module.app.dependency_overrides.clear()
