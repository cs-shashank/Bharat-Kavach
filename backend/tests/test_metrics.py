"""
Tests for the /metrics endpoint and EvaluationFramework.calculate_metrics().

Test 1: Integration test — GET /metrics in MOCK_MODE
Test 2: Unit test   — calculate_metrics() with a known synthetic confusion matrix
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out heavy / unavailable native modules BEFORE any app code is imported.
# cv2 (OpenCV) and whisper-related packages are not installed in the test env.
# ---------------------------------------------------------------------------
for _mod in ("cv2", "whisper_timestamped", "whisper"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


# ---------------------------------------------------------------------------
# Test 1 — Integration test: GET /metrics with MOCK_MODE=True
# ---------------------------------------------------------------------------

def test_get_metrics_mock_mode():
    """
    Call GET /metrics with MOCK_MODE forced to True.

    Asserts:
    - HTTP 200
    - All six required fields present in the response
    - mode == "mock"
    - precision >= 0.92
    - recall >= 0.90
    - false_positive_rate <= 0.05
    - confusion_matrix tp + tn + fp + fn == total_samples
    """
    import main as app_module
    from unittest.mock import patch
    from fastapi.testclient import TestClient

    client = TestClient(app_module.app)

    with patch.object(app_module, "MOCK_MODE", True):
        response = client.get("/metrics")

    assert response.status_code == 200, (
        f"Expected HTTP 200, got {response.status_code}: {response.text}"
    )

    body = response.json()

    # All six required fields must be present
    required_fields = {
        "mode", "precision", "recall",
        "false_positive_rate", "confusion_matrix", "total_samples",
    }
    missing = required_fields - set(body.keys())
    assert not missing, f"Missing fields in /metrics response: {missing}"

    # mode must be "mock"
    assert body["mode"] == "mock", (
        f"Expected mode='mock', got mode={body['mode']!r}"
    )

    # Precision / recall / FPR thresholds
    assert body["precision"] >= 0.92, (
        f"Expected precision >= 0.92, got {body['precision']}"
    )
    assert body["recall"] >= 0.90, (
        f"Expected recall >= 0.90, got {body['recall']}"
    )
    assert body["false_positive_rate"] <= 0.05, (
        f"Expected false_positive_rate <= 0.05, got {body['false_positive_rate']}"
    )

    # Confusion matrix totals must equal total_samples
    cm = body["confusion_matrix"]
    cm_sum = cm["tp"] + cm["tn"] + cm["fp"] + cm["fn"]
    assert cm_sum == body["total_samples"], (
        f"Expected tp+tn+fp+fn == total_samples ({body['total_samples']}), "
        f"but got cm_sum={cm_sum} (cm={cm})"
    )


# ---------------------------------------------------------------------------
# Test 2 — Unit test: calculate_metrics() with a synthetic confusion matrix
#
# Confusion matrix under test: {tp:3, tn:3, fp:1, fn:1}
#   precision = tp / (tp + fp) = 3 / 4 = 0.75
#   recall    = tp / (tp + fn) = 3 / 4 = 0.75
#   fpr       = fp / (fp + tn) = 1 / 4 = 0.25
# ---------------------------------------------------------------------------

def test_calculate_metrics_known_confusion_matrix():
    """
    Instantiate EvaluationFramework with api_key='test' (run_eval is NOT called)
    and pass a hand-crafted results list that yields a known confusion matrix.

    Asserts:
    - precision == 0.75
    - recall    == 0.75
    - false_positive_rate == 0.25
    """
    # Stub out the AI-engine constructors so they don't try to load real models
    # with the dummy api_key.
    behavioral_mock = MagicMock()
    legal_rag_mock = MagicMock()
    protocol_mock = MagicMock()

    with (
        MagicMock() as _,  # keep context manager syntax clean
    ):
        pass  # no-op placeholder; real patching is done below

    from unittest.mock import patch

    with patch("ai_engines.behavioral.BehavioralClassifier", return_value=behavioral_mock), \
         patch("ai_engines.legal_rag.LegalRAG", return_value=legal_rag_mock), \
         patch("ai_engines.protocol.ProtocolVerifier", return_value=protocol_mock):

        from tests.eval_metrics import EvaluationFramework
        framework = EvaluationFramework(api_key="test")

    # Build synthetic results: {tp:3, tn:3, fp:1, fn:1}
    results = []

    # 3 true positives  — expected="scam", predicted="scam"
    for i in range(3):
        results.append({"expected": "scam", "predicted": "scam"})

    # 3 true negatives  — expected="legit", predicted="legit"
    for i in range(3):
        results.append({"expected": "legit", "predicted": "legit"})

    # 1 false positive  — expected="legit", predicted="scam"
    results.append({"expected": "legit", "predicted": "scam"})

    # 1 false negative  — expected="scam", predicted="legit"
    results.append({"expected": "scam", "predicted": "legit"})

    metrics = framework.calculate_metrics(results)

    assert metrics["precision"] == 0.75, (
        f"Expected precision=0.75, got {metrics['precision']}"
    )
    assert metrics["recall"] == 0.75, (
        f"Expected recall=0.75, got {metrics['recall']}"
    )
    assert metrics["false_positive_rate"] == 0.25, (
        f"Expected false_positive_rate=0.25, got {metrics['false_positive_rate']}"
    )
