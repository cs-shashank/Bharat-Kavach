"""
eval_pipeline.py — Bharat Kavach Phase 1

EvaluationPipeline runs all four AI components against the EvalManifest and
produces per-component precision/recall/F1/FPR metrics.

EvalResultStore persists each run's metrics to disk (append-only, never overwrites).
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Rate limiter: Gemini free tier = 15 requests/minute = 1 req / 4 seconds
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple token-bucket rate limiter for Gemini API calls."""

    def __init__(self, calls_per_minute: int = 12):
        self._min_interval = 60.0 / calls_per_minute
        self._last_call: float = 0.0

    def wait(self):
        """Block until it is safe to make the next API call."""
        elapsed = time.monotonic() - self._last_call
        wait_for = self._min_interval - elapsed
        if wait_for > 0:
            time.sleep(wait_for)
        self._last_call = time.monotonic()


_gemini_limiter = _RateLimiter(calls_per_minute=14)  # 14/min stays under 15/min free tier

# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = _BACKEND_DIR / "data" / "eval_results"
MANIFEST_PATH = _BACKEND_DIR / "data" / "eval_manifest.json"
TEST_ASSETS_DIR = _BACKEND_DIR / "data" / "test_assets"

# Thresholds used by CIGate
THRESHOLDS = {
    "BehavioralClassifier": {"precision": 0.85, "fpr": 0.10},
    "LegalRAG":             {"precision": 0.80},
    "VisionForensics":      {"precision": 0.75},
    "CurrencyVerifier":     {"precision": 0.75},
}

# Minimum sample count before a threshold check is considered meaningful
MIN_SAMPLES_FOR_GATE = 10

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ComponentMetrics:
    """Per-component evaluation metrics for one pipeline run."""
    component: str
    sample_count: int
    precision: float
    recall: float
    f1: float
    fpr: float
    confusion: dict = field(default_factory=lambda: {"tp": 0, "tn": 0, "fp": 0, "fn": 0})


@dataclass
class EvalRunResult:
    """Complete result of one EvaluationPipeline run."""
    run_id: str                          # "{git_sha}_{iso_timestamp}"
    manifest_version: int
    git_commit_sha: str
    run_at: str                          # ISO 8601 UTC
    per_component: dict = field(default_factory=dict)   # str -> ComponentMetrics
    eval_errors: list = field(default_factory=list)     # {sample_id, component, error_type, msg}
    raw_results: list = field(default_factory=list)     # full per-sample detail


# ---------------------------------------------------------------------------
# EvalResultStore
# ---------------------------------------------------------------------------


class EvalResultStore:
    """Append-only store for EvalRunResult objects. Never deletes or overwrites."""

    def __init__(self, results_dir: Path = RESULTS_DIR):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _run_id_to_filename(self, run_id: str) -> str:
        """Convert run_id to filesystem-safe filename (replace : with -)."""
        safe = run_id.replace(":", "-")
        return f"eval_{safe}.json"

    def save(self, run_result: EvalRunResult) -> Path:
        """Write result file. Raises FileExistsError if run_id already exists."""
        filename = self._run_id_to_filename(run_result.run_id)
        path = self.results_dir / filename
        if path.exists():
            raise FileExistsError(f"Result file already exists: {path}")

        # Serialise ComponentMetrics to dicts
        serialisable = {
            "run_id": run_result.run_id,
            "manifest_version": run_result.manifest_version,
            "git_commit_sha": run_result.git_commit_sha,
            "run_at": run_result.run_at,
            "per_component": {
                k: {
                    "component": v.component,
                    "sample_count": v.sample_count,
                    "precision": v.precision,
                    "recall": v.recall,
                    "f1": v.f1,
                    "fpr": v.fpr,
                    "confusion": v.confusion,
                }
                for k, v in run_result.per_component.items()
            },
            "eval_errors": run_result.eval_errors,
            "raw_results": run_result.raw_results,
        }
        path.write_text(json.dumps(serialisable, indent=2), encoding="utf-8")
        return path

    def load(self, run_id: str) -> EvalRunResult:
        """Load a result file by run_id."""
        filename = self._run_id_to_filename(run_id)
        path = self.results_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"No result file for run_id={run_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        per_component = {
            k: ComponentMetrics(**v)
            for k, v in data.get("per_component", {}).items()
        }
        return EvalRunResult(
            run_id=data["run_id"],
            manifest_version=data["manifest_version"],
            git_commit_sha=data["git_commit_sha"],
            run_at=data["run_at"],
            per_component=per_component,
            eval_errors=data.get("eval_errors", []),
            raw_results=data.get("raw_results", []),
        )

    def list_runs(self) -> list:
        """Return all run_ids sorted ascending by timestamp."""
        files = sorted(self.results_dir.glob("eval_*.json"))
        return [f.stem[len("eval_"):].replace("-", ":", 2) for f in files]


# ---------------------------------------------------------------------------
# EvaluationPipeline
# ---------------------------------------------------------------------------


class EvaluationPipeline:
    """
    Runs all four AI components against an EvalManifest and produces
    per-component precision/recall/F1/FPR metrics.

    Extends the logic of EvaluationFramework in backend/tests/eval_metrics.py
    without modifying that class.
    """

    def __init__(self, api_key: str, manifest_path: Path = MANIFEST_PATH):
        self.api_key = api_key
        self.manifest_path = manifest_path
        self.store = EvalResultStore()
        self._behavioral = None
        self._legal_rag = None
        self._vision = None
        self._currency = None

    def _get_git_sha(self) -> str:
        """Return short git commit SHA, or 'unknown' if git is unavailable."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(_BACKEND_DIR),
            )
            sha = result.stdout.strip()
            return sha if sha else "unknown"
        except Exception:
            return "unknown"

    def _init_engines(self):
        """Lazy-initialise AI engines on first use."""
        if self._behavioral is None:
            sys.path.insert(0, str(_BACKEND_DIR))
            from ai_engines.behavioral import BehavioralClassifier
            from ai_engines.legal_rag import LegalRAG
            from ai_engines.currency import CurrencyVerifier
            from ai_engines.protocol import ProtocolVerifier
            self._behavioral = BehavioralClassifier(api_key=self.api_key)
            self._legal_rag = LegalRAG(api_key=self.api_key)
            self._currency = CurrencyVerifier()
            self._protocol = ProtocolVerifier()

    def load_manifest(self, path: Path = None) -> dict:
        """Load and return the EvalManifest JSON."""
        p = path or self.manifest_path
        if not p.exists():
            raise FileNotFoundError(
                f"EvalManifest not found at {p}. "
                "Create it or run task 8.1 to generate the bootstrap manifest."
            )
        return json.loads(p.read_text(encoding="utf-8"))

    def compute_metrics(self, results: list) -> ComponentMetrics:
        """
        Compute precision, recall, F1, FPR from a list of
        {'ground_truth': str, 'predicted': str} dicts.

        Positive class = 'scam' (or 'forged'/'counterfeit' for image components).
        Uses the same formula as EvaluationFramework.calculate_metrics().
        """
        # Normalise labels: any non-'legit'/'genuine'/'authentic' is positive
        NEGATIVE_LABELS = {"legit", "genuine", "authentic"}

        tp = sum(1 for r in results if r["ground_truth"] not in NEGATIVE_LABELS and r["predicted"] not in NEGATIVE_LABELS)
        tn = sum(1 for r in results if r["ground_truth"] in NEGATIVE_LABELS and r["predicted"] in NEGATIVE_LABELS)
        fp = sum(1 for r in results if r["ground_truth"] in NEGATIVE_LABELS and r["predicted"] not in NEGATIVE_LABELS)
        fn = sum(1 for r in results if r["ground_truth"] not in NEGATIVE_LABELS and r["predicted"] in NEGATIVE_LABELS)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)

        return ComponentMetrics(
            component="",
            sample_count=len(results),
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            fpr=round(fpr, 4),
            confusion={"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        )

    def delta(self, run_a: EvalRunResult, run_b: EvalRunResult) -> dict:
        """
        Return per-metric arithmetic differences: run_b - run_a for each
        shared component and metric.
        """
        result = {}
        for component in set(run_a.per_component) & set(run_b.per_component):
            a = run_a.per_component[component]
            b = run_b.per_component[component]
            result[component] = {
                "precision": round(b.precision - a.precision, 4),
                "recall":    round(b.recall    - a.recall,    4),
                "f1":        round(b.f1        - a.f1,        4),
                "fpr":       round(b.fpr       - a.fpr,       4),
            }
        return result

    def run(self, manifest: dict = None) -> EvalRunResult:
        """
        Run all four components against the EvalManifest and return metrics.

        For each sample:
        - Skip with a warning if a required file_path is absent.
        - On component exception, record in eval_errors and continue.
        - Print a per-component summary table to stdout on completion.
        - Save result via EvalResultStore.
        """
        if manifest is None:
            manifest = self.load_manifest()

        self._init_engines()

        git_sha = self._get_git_sha()
        run_at  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        run_id  = f"{git_sha}_{run_at}"

        # Accumulate (ground_truth, predicted) pairs per component
        component_pairs: dict[str, list] = {
            "BehavioralClassifier": [],
            "LegalRAG": [],
            "VisionForensics": [],
            "CurrencyVerifier": [],
        }
        eval_errors: list = []
        raw_results: list = []

        for idx, sample in enumerate(manifest.get("samples", []), 1):
            sample_id   = sample["sample_id"]
            sample_type = sample["sample_type"]
            ground_truth = sample["ground_truth"]
            applicable  = sample.get("applicable_components", [])

            total = len(manifest.get("samples", []))
            if idx % 10 == 0 or idx == 1:
                print(f"[EvalPipeline] Processing sample {idx}/{total}: {sample_id}", flush=True)

            # Resolve file path for image samples
            if sample_type in ("document_image", "currency_image"):
                subdir = "documents" if sample_type == "document_image" else "currency"
                file_path = TEST_ASSETS_DIR / subdir / sample.get("file_path", "")
                if not file_path.exists():
                    print(f"[EvalPipeline] WARNING: file not found, skipping {sample_id}: {file_path}", file=sys.stderr)
                    continue

            # --- BehavioralClassifier ---
            if "BehavioralClassifier" in applicable and sample_type == "transcript":
                try:
                    transcript = sample.get("transcript", "")
                    _gemini_limiter.wait()
                    result = self._behavioral.analyze_transcript(transcript)
                    risk_score = result.confidence * 100
                    # Predict scam if risk_score > 85 (calibrated threshold)
                    predicted = "scam" if risk_score > 85 else "legit"
                    component_pairs["BehavioralClassifier"].append({
                        "ground_truth": ground_truth, "predicted": predicted
                    })
                    raw_results.append({
                        "sample_id": sample_id, "component": "BehavioralClassifier",
                        "ground_truth": ground_truth, "predicted": predicted,
                        "risk_score": risk_score,
                    })
                except Exception as exc:
                    eval_errors.append({
                        "sample_id": sample_id, "component": "BehavioralClassifier",
                        "error_type": type(exc).__name__, "error_msg": str(exc),
                    })

            # --- LegalRAG ---
            if "LegalRAG" in applicable and sample_type == "transcript":
                try:
                    transcript = sample.get("transcript", "")
                    _gemini_limiter.wait()
                    findings = self._legal_rag.verify_legal_claims(transcript)
                    _gemini_limiter.wait()
                    violations = self._protocol.check_violations(transcript)
                    myths_found = any(f.verdict == "confirmed_false" for f in findings)
                    predicted = "scam" if (myths_found or len(violations) > 0) else "legit"
                    component_pairs["LegalRAG"].append({
                        "ground_truth": ground_truth, "predicted": predicted
                    })
                    raw_results.append({
                        "sample_id": sample_id, "component": "LegalRAG",
                        "ground_truth": ground_truth, "predicted": predicted,
                        "myths_found": myths_found,
                    })
                except Exception as exc:
                    eval_errors.append({
                        "sample_id": sample_id, "component": "LegalRAG",
                        "error_type": type(exc).__name__, "error_msg": str(exc),
                    })

            # --- VisionForensics ---
            if "VisionForensics" in applicable and sample_type == "document_image":
                try:
                    image_bytes = file_path.read_bytes()
                    # VisionForensics requires api_key — lazy init
                    if self._vision is None:
                        from ai_engines.vision import VisionForensics
                        self._vision = VisionForensics(
                            api_key=self.api_key,
                            legal_rag_engine=self._legal_rag,
                        )
                    _gemini_limiter.wait()
                    result = self._vision.analyze_document(image_bytes)
                    predicted = "forged" if result.verdict.lower().startswith("likely fake") or "fake" in result.verdict.lower() else "authentic"
                    component_pairs["VisionForensics"].append({
                        "ground_truth": ground_truth, "predicted": predicted
                    })
                    raw_results.append({
                        "sample_id": sample_id, "component": "VisionForensics",
                        "ground_truth": ground_truth, "predicted": predicted,
                        "verdict": result.verdict, "confidence": result.confidence_score,
                    })
                except Exception as exc:
                    eval_errors.append({
                        "sample_id": sample_id, "component": "VisionForensics",
                        "error_type": type(exc).__name__, "error_msg": str(exc),
                    })

            # --- CurrencyVerifier ---
            if "CurrencyVerifier" in applicable and sample_type == "currency_image":
                try:
                    image_bytes = file_path.read_bytes()
                    result = self._currency.verify_note(image_bytes)
                    is_suspicious = result.get("signals", {}).get("is_suspicious", False)
                    predicted = "counterfeit" if is_suspicious else "genuine"
                    component_pairs["CurrencyVerifier"].append({
                        "ground_truth": ground_truth, "predicted": predicted
                    })
                    raw_results.append({
                        "sample_id": sample_id, "component": "CurrencyVerifier",
                        "ground_truth": ground_truth, "predicted": predicted,
                        "is_suspicious": is_suspicious,
                    })
                except Exception as exc:
                    eval_errors.append({
                        "sample_id": sample_id, "component": "CurrencyVerifier",
                        "error_type": type(exc).__name__, "error_msg": str(exc),
                    })

        # Compute metrics per component
        per_component: dict[str, ComponentMetrics] = {}
        for component_name, pairs in component_pairs.items():
            metrics = self.compute_metrics(pairs)
            metrics.component = component_name
            per_component[component_name] = metrics

        run_result = EvalRunResult(
            run_id=run_id,
            manifest_version=manifest.get("manifest_version", 0),
            git_commit_sha=git_sha,
            run_at=run_at,
            per_component=per_component,
            eval_errors=eval_errors,
            raw_results=raw_results,
        )

        # Print summary table
        self._print_summary(run_result)

        # Save to EvalResultStore
        self.store.save(run_result)

        return run_result

    def _print_summary(self, run_result: EvalRunResult):
        """Print a per-component metrics table to stdout."""
        print("\n" + "=" * 68)
        print("  BHARAT KAVACH EVALUATION PIPELINE — RESULTS")
        print("=" * 68)
        print(f"  Run ID : {run_result.run_id}")
        print(f"  Manifest version: {run_result.manifest_version}")
        print(f"  Errors : {len(run_result.eval_errors)}")
        print("-" * 68)
        header = f"  {'Component':<25} {'N':>5} {'P':>7} {'R':>7} {'F1':>7} {'FPR':>7}"
        print(header)
        print("-" * 68)
        for name, m in run_result.per_component.items():
            if m.sample_count == 0:
                print(f"  {name:<25} {'0':>5}  {'—':>6}  {'—':>6}  {'—':>6}  {'—':>6}")
            else:
                print(f"  {name:<25} {m.sample_count:>5} {m.precision:>7.3f} {m.recall:>7.3f} {m.f1:>7.3f} {m.fpr:>7.3f}")
        print("=" * 68 + "\n")
