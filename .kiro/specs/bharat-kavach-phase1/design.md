# Design Document — Bharat Kavach Phase 1

## Overview

Phase 1 augments the existing Bharat Kavach backend with four capabilities that are strictly additive — nothing in the existing AI engine pipeline is modified:

1. **Auditable Evidence Export** — `EvidenceExporter` wraps all component outputs into a cryptographically signed JSON bundle and generates a human-readable PDF summary via `reportlab`.
2. **Labeled Test Dataset** — `EvalManifest` (JSON) declares a versioned, cited corpus of transcripts, document images, and currency images.
3. **Batch Evaluation Pipeline** — `EvaluationPipeline` extends the existing `EvaluationFramework` to cover all four AI components with per-component precision/recall/F1/FPR metrics.
4. **CI Quality Gate** — `ci_eval.py` invokes `EvaluationPipeline` and exits non-zero if any component falls below its threshold.

All new modules live under `backend/` alongside the existing structure. No existing file is deleted or altered; only `backend/main.py` gains two new endpoints, and `backend/data/legal_kb.json` gains a `bns_verified` field on each entry.

---

## Architecture

### How EvidenceExporter Fits into the Existing Pipeline

```
POST /analyze  ──► BehavioralClassifier ──► AnalysisResult
                ──► LegalRAG            ──► List[LegalClaim]
                ──► VisionForensics     ──► VisionAnalysisResult   (if image uploaded)
                ──► CurrencyVerifier    ──► Dict                   (if currency image uploaded)
                         │
                         ▼  (after all engines return)
               EvidenceExporter.build_bundle(...)
                         │
                ┌────────┴──────────┐
                ▼                   ▼
        BK-{id}.evidence.json   BK-{id}.summary.pdf
        (backend/data/           (backend/data/
         evidence_exports/)       evidence_exports/)
                         │
                         ▼
              GET /cases/{id}/evidence
              GET /cases/{id}/evidence/download
```

`EvidenceExporter` never calls any AI engine directly. It only receives the already-computed outputs as Python objects and serialises them. The existing `/analyze` endpoint assembles component results and passes them to `EvidenceExporter.build_bundle()` before returning its own response.

### Evaluation Sub-System

```
EvalManifest (backend/data/eval_manifest.json)
          │
          ▼
EvaluationPipeline.run(manifest)
   ├── BehavioralClassifier  ◄── transcript samples
   ├── LegalRAG              ◄── transcript samples
   ├── VisionForensics       ◄── document_image samples
   └── CurrencyVerifier      ◄── currency_image samples
          │
          ▼
EvalResultStore.save(metrics)   ──► backend/data/eval_results/eval_{sha}_{ts}.json
          │
          ▼
ci_eval.py  ──► compare metrics vs thresholds ──► exit 0 | 1
```

---

## Directory and File Layout for New Artifacts

```
backend/
├── ai_engines/          (unchanged)
├── data/
│   ├── legal_kb.json                   ← add bns_verified field to each entry
│   ├── eval_manifest.json              ← new: EvalManifest (versioned)
│   ├── eval_results/                   ← new directory
│   │   └── eval_{git_sha}_{ts}.json   ← per-run result files
│   ├── evidence_exports/               ← new directory
│   │   ├── BK-{bundle_id}.evidence.json
│   │   └── BK-{bundle_id}.summary.pdf
│   └── test_assets/                    ← new directory
│       ├── transcripts/                ← (samples are inline in manifest; this dir is reserved)
│       ├── documents/                  ← document image files referenced by manifest
│       └── currency/                   ← currency image files referenced by manifest
├── logs/
│   └── evidence_export_failures.log   ← fallback failure log (plain-text append)
├── schemas/
│   └── evidence_bundle.schema.json    ← published JSON Schema for bundle validation
├── scripts/
│   └── ci_eval.py                     ← CIGate executable
├── services/
│   └── evidence_exporter.py           ← new: EvidenceExporter module
├── tests/
│   ├── eval_metrics.py                ← unchanged
│   ├── test_evidence_exporter.py      ← new: property tests
│   ├── test_eval_pipeline.py          ← new: property tests
│   └── test_ci_gate.py                ← new: property tests
├── database.py                        (unchanged)
└── main.py                            ← add two new endpoints only
```

---

## EvidenceBundle JSON Schema

### Full Field Definitions

```json
{
  "bundle_id": "<UUID v4 string>",
  "analyzed_at": "<ISO 8601 UTC, e.g. 2026-01-15T10:30:00Z>",
  "case_id": "<integer, FK to CaseReport.id>",
  "sha256_hash": "<hex string, SHA-256 over canonical fields>",

  "model_registry": {
    "BehavioralClassifier": "<model_id string, e.g. gemini-2.0-flash>",
    "LegalRAG":             "<model_id string>",
    "VisionForensics":      "<model_id string>",
    "CurrencyVerifier":     "opencv-roi-v1"
  },

  "chain_of_custody": [
    {
      "step":          1,
      "component":     "BehavioralClassifier",
      "artifact_type": "transcript",
      "action":        "analyze_transcript completed",
      "timestamp":     "2026-01-15T10:30:01Z"
    }
  ],

  "component_verdicts": {
    "BehavioralClassifier": {
      "verdict":    "Financial Demand / UPI Request",
      "confidence": 0.91,
      "details": {
        "current_stage":         "Financial Demand / UPI Request",
        "reasoning":             "...",
        "red_flags":             ["Pay via UPI", "Avoid arrest"],
        "intervention_required": true
      }
    },
    "LegalRAG": {
      "verdict":    "confirmed_false",
      "confidence": 1.0,
      "details": {
        "claims_verified": 3,
        "myths_detected":  2,
        "findings": [
          {
            "claim_extracted":  "...",
            "verdict":          "confirmed_false",
            "explanation":      "...",
            "matched_kb_id":    "digital_arrest_myth_1",
            "relevant_provision": "BNSS Section 43"
          }
        ]
      }
    },
    "VisionForensics": {
      "verdict":    "not_applicable",
      "confidence": null,
      "details":    null
    },
    "CurrencyVerifier": {
      "verdict":    "not_applicable",
      "confidence": null,
      "details":    null
    }
  }
}
```

### Canonical Serialisation for SHA-256

The hash is computed over a Python dict containing all top-level keys **except** `sha256_hash`, serialised with `json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`, then UTF-8 encoded before hashing. This deterministic form eliminates whitespace and key-order variance.

---

## EvidenceExporter Class Design

### Module: `backend/services/evidence_exporter.py`

```python
class EvidenceExporter:
    EXPORTS_DIR   = "backend/data/evidence_exports"
    FAILURE_LOG   = "backend/logs/evidence_export_failures.log"
    SCHEMA_PATH   = "backend/schemas/evidence_bundle.schema.json"

    def build_bundle(
        self,
        case_id:         int,
        transcript:      str,
        behavioral_result: AnalysisResult | None,
        legal_findings:  list[LegalClaim] | None,
        vision_result:   VisionAnalysisResult | None,
        currency_result: dict | None,
        model_registry:  dict[str, str],
    ) -> EvidenceBundle:
        """Assemble all component outputs into an EvidenceBundle."""

    def compute_hash(self, bundle: EvidenceBundle) -> str:
        """Return SHA-256 hex of canonical serialisation excluding sha256_hash."""

    def verify_hash(self, bundle: EvidenceBundle) -> bool:
        """Return True if bundle.sha256_hash matches recomputed hash."""

    def export_json(self, bundle: EvidenceBundle) -> Path:
        """
        Write BK-{bundle_id}.evidence.json to EXPORTS_DIR.
        On any serialisation exception for a component:
          - record serialisation_error in chain_of_custody
          - continue with partial export
        On filesystem write failure:
          - attempt fallback plain-text append to FAILURE_LOG
        Returns the Path of the written file.
        """

    def export_pdf(self, bundle: EvidenceBundle) -> Path:
        """
        Generate BK-{bundle_id}.summary.pdf using reportlab.
        Returns the Path of the written file.
        """
```

### Dual-Path Failure Logic (Primary → Fallback)

```
export_json(bundle)
  │
  ├─► try: json.dumps(bundle) → write to EXPORTS_DIR/BK-{id}.evidence.json
  │         ├─► SUCCESS: return Path
  │         └─► ComponentSerializationError:
  │               append {action: "serialisation_error: TypeError"} to chain_of_custody
  │               write partial export (other components intact) → return Path
  │
  └─► FilesystemError (disk full, permissions, etc.):
        ├─► try: open(FAILURE_LOG, 'a') → plain-text append:
        │       "FAILURE|{bundle_id}|{timestamp}|{exception_type}|{exception_msg}\n"
        │   └─► If this also fails: swallow silently (log to stderr only)
        └─► raise EvidenceExportError(bundle_id, exception)
```

The fallback path uses `open(..., 'a')` with a plain-text format (not JSON write) so that whatever caused the primary failure (JSON serialisation bug, full disk partition) is less likely to also break the fallback.

### PDF Structure (reportlab)

The PDF is generated using `reportlab.platypus` with a `SimpleDocTemplate`. Sections in order:

1. **Header** — "BHARAT KAVACH — FORENSIC EVIDENCE SUMMARY", bundle_id, case_id
2. **Analysis Timestamp** — `analyzed_at` formatted as human-readable
3. **Component Verdicts Table** — 4 rows (one per component), columns: Component | Verdict | Confidence
   - `not_applicable` rows show `—` in Verdict and Confidence columns
4. **Chain of Custody Timeline** — each step on its own line with timestamp
5. **SHA-256 Integrity Footer** — hash value in monospace font
6. **Disclaimer** — fixed text: "This document is an automated forensic estimate generated by Bharat Kavach AI. It does not constitute legal advice, a certified forensic examination report, or an official government document."

---

## EvalManifest Schema Design

### File: `backend/data/eval_manifest.json`

```json
{
  "manifest_version": 1,
  "created_at": "2026-01-15T10:00:00Z",
  "description": "Bharat Kavach Phase 1 labeled evaluation dataset",
  "samples": [
    {
      "sample_id":     "tr_scam_001",
      "sample_type":   "transcript",
      "ground_truth":  "scam",
      "transcript":    "FedEx: Your parcel has been seized...",
      "source_citation": "https://mha.gov.in/advisory/2024/digital-arrest-01",
      "tricky_negative": false,
      "applicable_components": ["BehavioralClassifier", "LegalRAG"]
    },
    {
      "sample_id":     "doc_auth_001",
      "sample_type":   "document_image",
      "ground_truth":  "authentic",
      "file_path":     "documents/court_summons_001.jpg",
      "source_citation": "https://example-court-record-url.in/case/442",
      "tricky_negative": false,
      "applicable_components": ["VisionForensics"]
    },
    {
      "sample_id":     "cur_genuine_001",
      "sample_type":   "currency_image",
      "ground_truth":  "genuine",
      "file_path":     "currency/500_genuine_001.jpg",
      "denomination":  500,
      "source_citation": "Kaggle: Indian Currency Dataset v2.1, https://kaggle.com/datasets/...",
      "tricky_negative": false,
      "applicable_components": ["CurrencyVerifier"]
    }
  ]
}
```

### Field Definitions

| Field | Type | Required | Notes |
|---|---|---|---|
| `manifest_version` | integer | Yes | Incremented on every modification |
| `created_at` | ISO 8601 string | Yes | Creation timestamp |
| `description` | string | Yes | Human description |
| `samples[].sample_id` | string | Yes | Unique across manifest |
| `samples[].sample_type` | enum | Yes | `transcript`, `document_image`, `currency_image` |
| `samples[].ground_truth` | enum | Yes | `scam`/`legit` for transcripts; `authentic`/`forged` for docs; `genuine`/`counterfeit` for currency |
| `samples[].transcript` | string | If transcript | Inline text |
| `samples[].file_path` | string | If image | Relative to `backend/data/test_assets/{type}/` |
| `samples[].denomination` | integer | If currency | ₹100, ₹200, ₹500, ₹2000 |
| `samples[].source_citation` | string | Yes | URL or MHA advisory reference |
| `samples[].tricky_negative` | boolean | Yes | True for legit samples with legal-sounding terms |
| `samples[].applicable_components` | list[string] | Yes | Which engines to run this sample through |

---

## EvaluationPipeline Design

### Module: `backend/services/eval_pipeline.py`

`EvaluationPipeline` extends the logic of the existing `EvaluationFramework` in `backend/tests/eval_metrics.py`. It does not replace or modify that class — it calls the same decision threshold logic and wraps it to handle all four components and the manifest format.

```python
class EvaluationPipeline:
    THRESHOLDS = {
        "BehavioralClassifier": {"precision": 0.85, "fpr": 0.10},
        "LegalRAG":             {"precision": 0.80},
        "VisionForensics":      {"precision": 0.75},
        "CurrencyVerifier":     {"precision": 0.75},
    }

    def __init__(self, api_key: str, manifest_path: str = None):
        """Initialise all four AI engines + EvaluationFramework."""

    def load_manifest(self, path: str) -> dict:
        """Load and validate EvalManifest JSON."""

    def run(self, manifest: dict) -> EvalRunResult:
        """
        For each sample in manifest.samples:
          - Skip (log warning) if file_path does not exist
          - Run through applicable_components
          - On component exception: record as eval_error, exclude from metrics
          - Collect predictions and ground-truth labels per component
        Compute per-component metrics.
        Return EvalRunResult.
        """

    def compute_metrics(self, results: list[SampleResult]) -> ComponentMetrics:
        """
        For a list of (ground_truth, predicted) pairs:
        Compute precision, recall, F1, FPR.
        Uses same formula as EvaluationFramework.calculate_metrics().
        """

    def delta(self, run_a: EvalRunResult, run_b: EvalRunResult) -> dict:
        """
        Return per-metric delta: run_b.metrics - run_a.metrics for each component.
        """
```

### Decision Threshold (preserved from EvaluationFramework)

For transcript samples, a prediction of `"scam"` is made when **any** of:
- `risk_score > 60` (where `risk_score = behavioral.confidence * 100`)
- Any `LegalClaim.verdict == "confirmed_false"` is found
- Any protocol violations are found

This is identical to the existing `EvaluationFramework.run_eval()` logic.

### EvalRunResult Structure

```python
@dataclass
class EvalRunResult:
    run_id:           str               # "{git_sha}_{iso_timestamp}"
    manifest_version: int
    git_commit_sha:   str
    run_at:           str               # ISO 8601
    per_component:    dict[str, ComponentMetrics]
    eval_errors:      list[dict]        # {sample_id, component, error_type, error_msg}
    raw_results:      list[dict]        # full per-sample detail

@dataclass
class ComponentMetrics:
    component:    str
    sample_count: int
    precision:    float
    recall:       float
    f1:           float
    fpr:          float
    confusion:    dict   # {tp, tn, fp, fn}
```

---

## EvalResultStore Design

### Storage Convention

Each pipeline run writes **one** result file. Files are never deleted or overwritten:

```
backend/data/eval_results/
└── eval_{git_commit_sha}_{iso_timestamp}.json
    e.g.: eval_a3f9b12_2026-01-15T10-30-00Z.json
```

ISO timestamp in filenames uses `-` instead of `:` to be filesystem-safe on Windows.

### Result File Schema

```json
{
  "run_id":           "a3f9b12_2026-01-15T10:30:00Z",
  "manifest_version": 3,
  "git_commit_sha":   "a3f9b12",
  "run_at":           "2026-01-15T10:30:00Z",
  "per_component": {
    "BehavioralClassifier": {
      "sample_count": 200,
      "precision":    0.91,
      "recall":       0.88,
      "f1":           0.895,
      "fpr":          0.06,
      "confusion":    {"tp": 176, "tn": 18, "fp": 2, "fn": 4}
    }
  },
  "eval_errors": [],
  "raw_results":  []
}
```

### EvalResultStore Class

```python
class EvalResultStore:
    RESULTS_DIR = "backend/data/eval_results"

    def save(self, run_result: EvalRunResult) -> Path:
        """Write result file; never overwrites existing files."""

    def load(self, run_id: str) -> EvalRunResult:
        """Load a specific result file by run_id."""

    def list_runs(self) -> list[str]:
        """Return all run_ids sorted by timestamp ascending."""
```

---

## CIGate Design

### Script: `backend/scripts/ci_eval.py`

The script is a standalone executable requiring only the `.env` variables (`GOOGLE_API_KEY`) that the rest of the backend already uses.

### Logic

```
1. Load EvalManifest from backend/data/eval_manifest.json
2. Instantiate EvaluationPipeline(api_key=GOOGLE_API_KEY)
3. run_result = pipeline.run(manifest)
4. store.save(run_result)
5. For each component in [BehavioralClassifier, LegalRAG, VisionForensics, CurrencyVerifier]:
   a. If sample_count < 10: print WARNING, skip threshold check for this component
   b. Else: compare metrics against THRESHOLDS
      - BehavioralClassifier: precision >= 0.85 AND fpr <= 0.10
      - LegalRAG:             precision >= 0.80
      - VisionForensics:      precision >= 0.75
      - CurrencyVerifier:     precision >= 0.75
   c. Collect failures
6. If any failures: print failure details, sys.exit(1)
7. Else: print PASS summary table, sys.exit(0)
```

### Threshold Table

| Component | Metric | Minimum |
|---|---|---|
| BehavioralClassifier | Precision | 0.85 |
| BehavioralClassifier | FPR | ≤ 0.10 |
| LegalRAG | Precision | 0.80 |
| VisionForensics | Precision | 0.75 |
| CurrencyVerifier | Precision | 0.75 |

### stdout Pass Summary Format

```
══════════════════════════════════════════════════════════
  BHARAT KAVACH CI GATE — PASS
══════════════════════════════════════════════════════════
  Component              Precision   FPR    Threshold
  BehavioralClassifier   0.91        0.06   P≥0.85 / FPR≤0.10  ✓
  LegalRAG               0.88        —      P≥0.80              ✓
  VisionForensics        0.82        —      P≥0.75              ✓
  CurrencyVerifier       0.79        —      P≥0.75              ✓
══════════════════════════════════════════════════════════
  Run ID: a3f9b12_2026-01-15T10:30:00Z
```

---

## API Endpoint Design

### GET `/cases/{case_id}/evidence`

**Purpose:** Return the full EvidenceBundle JSON for a case, plus a `pdf_url` download link.

**Path parameter:** `case_id` — integer, must correspond to an existing `CaseReport.id`.

**Success Response (200):**
```json
{
  "bundle_id":   "550e8400-e29b-41d4-a716-446655440000",
  "analyzed_at": "2026-01-15T10:30:00Z",
  "case_id":     42,
  "sha256_hash": "a1b2c3...",
  "model_registry": { ... },
  "chain_of_custody": [ ... ],
  "component_verdicts": { ... },
  "pdf_url": "/cases/42/evidence/download"
}
```

**Error Response (404):**
```json
{"detail": "Case not found"}
```

**Implementation notes:**
- On first call for a case, `EvidenceExporter.build_bundle()` is called using data from `CaseReport` row, then `export_json()` and `export_pdf()` are called. The bundle is cached to disk; subsequent calls read the cached file.
- If the export files already exist (idempotent regeneration), they are served directly without re-running the exporter.

---

### GET `/cases/{case_id}/evidence/download`

**Purpose:** Stream the PDF summary file as a downloadable attachment.

**Path parameter:** `case_id` — integer.

**Success Response (200):**
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="BK-{bundle_id}.summary.pdf"`
- Body: binary PDF stream via FastAPI `FileResponse`

**Error Response (404):**
```json
{"detail": "Case not found"}
```

**Error Response (404, file missing):**
```json
{"detail": "PDF not yet generated for this case"}
```

**FastAPI implementation sketch:**
```python
@app.get("/cases/{case_id}/evidence")
async def get_case_evidence(case_id: int, db: Session = Depends(get_db)):
    case = db.query(CaseReport).filter(CaseReport.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    bundle = exporter.get_or_create_bundle(case)
    return {**bundle.dict(), "pdf_url": f"/cases/{case_id}/evidence/download"}

@app.get("/cases/{case_id}/evidence/download")
async def download_case_evidence_pdf(case_id: int, db: Session = Depends(get_db)):
    case = db.query(CaseReport).filter(CaseReport.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    pdf_path = exporter.get_pdf_path(case.bundle_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not yet generated for this case")
    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=pdf_path.name,
                        headers={"Content-Disposition": f"attachment; filename={pdf_path.name}"})
```

---

## Legal KB Schema Extension

### `bns_verified` Field

Each entry in `backend/data/legal_kb.json` gains one new boolean field:

```json
{
  "id":                  "digital_arrest_myth_1",
  "scam_claim_pattern":  "...",
  "reality":             "...",
  "relevant_provision":  "BNSS Section 43 (Physical Custody Required)",
  "confidence":          "high",
  "citation_note":       "...",
  "bns_verified":        true
}
```

`bns_verified: true` means the cited BNS/BNSS section number has been manually cross-checked against the current published statute text (Ministry of Law and Justice gazette).

`bns_verified: false` means the entry has been added but not yet independently verified.

### LegalRAG Annotation Logic

`LegalRAG.verify_legal_claims()` must check `bns_verified` on each matched KB entry. When `bns_verified == false`, the `LegalClaim` returned must have its `disclaimer` field set to:

```
"Citation not yet verified against current BNS/BNSS statute — treat as informational"
```

(The existing `disclaimer` field on `LegalClaim` is already defined as `"Informational — not legal advice"` by default; this replaces that default for unverified entries.)

### Expanding to 10+ Entries

The current KB has 5 entries. Phase 1 requires at least 10 distinct digital-arrest scam patterns. Five additional entries to be added (each with `bns_verified: true` after statute cross-check):

| New Entry ID | Pattern Coverage | Provision |
|---|---|---|
| `aadhaar_misuse_myth_1` | "Your Aadhaar is linked to money laundering" | BNS Section 318 (Cheating) |
| `ncrb_ip_myth_1` | "Your IP used for illegal activity / NCRB notice" | BNS Section 204 (Impersonation) |
| `bank_freeze_myth_1` | "Your account will be frozen / RBI compliance call" | BNSS Section 43 + BNS 318 |
| `drug_parcel_myth_1` | "Drugs found in parcel with your Aadhaar at customs" | BNS Section 204 + BNS 308 |
| `secret_case_myth_1` | "This is a secret/confidential investigation, tell no one" | BNSS Section 50 (Right to inform relatives) |

---

## Components and Interfaces

### EvidenceExporter (`backend/services/evidence_exporter.py`)

- **Inputs**: raw outputs from AI engines (as Python objects), `case_id`, `model_registry` dict
- **Outputs**: `EvidenceBundle` Pydantic model; side-effects of writing `.evidence.json` and `.summary.pdf` to `backend/data/evidence_exports/`
- **Dependencies**: `hashlib` (stdlib), `json` (stdlib), `uuid` (stdlib), `reportlab` (PDF), `pathlib` (stdlib)
- **Does NOT depend on**: any AI engine — receives already-computed outputs only
- **Interface with main.py**: called from the `/analyze` endpoint after all engine calls complete, and from the new `/cases/{id}/evidence` endpoint

### EvaluationPipeline (`backend/services/eval_pipeline.py`)

- **Inputs**: `EvalManifest` dict, API key
- **Outputs**: `EvalRunResult` dataclass; side-effect of writing to `EvalResultStore`
- **Dependencies**: all four AI engines (instantiated internally), `EvaluationFramework` (for threshold logic reuse), `subprocess`/`git` (for commit SHA)
- **Interface with ci_eval.py**: `pipeline.run(manifest)` → `EvalRunResult` passed to `CIGate.check()`

### EvalResultStore (`backend/services/eval_pipeline.py`, co-located class)

- **Inputs**: `EvalRunResult`
- **Outputs**: file path of saved result; loaded `EvalRunResult` on read
- **Dependencies**: `json`, `pathlib`, `os`
- **Storage**: `backend/data/eval_results/` — append-only, never deletes

### CIGate (`backend/scripts/ci_eval.py`)

- **Inputs**: `EvalRunResult.per_component`, threshold constants
- **Outputs**: `sys.exit(0)` or `sys.exit(1)` (exit code 2 for configuration errors)
- **Dependencies**: `EvaluationPipeline`, `EvalResultStore`, `os`, `sys`
- **Interface**: standalone script, no imports from `main.py`

### Legal KB (`backend/data/legal_kb.json` + `backend/ai_engines/legal_rag.py`)

- **Schema change**: add `bns_verified: bool` to each entry in `legal_kb.json`
- **Behaviour change in LegalRAG**: check `bns_verified` when building `LegalClaim.disclaimer`
- **No other change** to `LegalRAG` class

### FastAPI Endpoints (additions to `backend/main.py`)

- `GET /cases/{case_id}/evidence` — calls `EvidenceExporter.get_or_create_bundle(case)`
- `GET /cases/{case_id}/evidence/download` — streams PDF via `FileResponse`
- Both endpoints depend on: `EvidenceExporter`, `CaseReport` ORM, `get_db` dependency

---

## Data Models

### Pydantic Models (new, in `backend/services/evidence_exporter.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
import uuid

class ChainOfCustodyEntry(BaseModel):
    step:          int
    component:     str
    artifact_type: Literal["transcript", "document_image", "currency_image"]
    action:        str
    timestamp:     str   # ISO 8601

class ComponentVerdict(BaseModel):
    verdict:    str
    confidence: Optional[float]          # None for not_applicable
    details:    Optional[dict]           # None for not_applicable

class EvidenceBundle(BaseModel):
    bundle_id:        str = Field(default_factory=lambda: str(uuid.uuid4()))
    analyzed_at:      str
    case_id:          int
    sha256_hash:      str = ""           # populated by compute_hash()
    model_registry:   dict[str, str]
    chain_of_custody: list[ChainOfCustodyEntry]
    component_verdicts: dict[str, ComponentVerdict]
```

### Pydantic Models (new, in `backend/services/eval_pipeline.py`)

```python
from dataclasses import dataclass, field

@dataclass
class ComponentMetrics:
    component:    str
    sample_count: int
    precision:    float
    recall:       float
    f1:           float
    fpr:          float
    confusion:    dict

@dataclass
class EvalRunResult:
    run_id:           str
    manifest_version: int
    git_commit_sha:   str
    run_at:           str
    per_component:    dict[str, ComponentMetrics] = field(default_factory=dict)
    eval_errors:      list[dict] = field(default_factory=list)
    raw_results:      list[dict] = field(default_factory=list)
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

The property-based testing library used is **Hypothesis** (already present in the project's `.hypothesis/` directory). Each property test runs a minimum of 100 iterations.

Tag format in tests: `# Feature: bharat-kavach-phase1, Property N: <title>`

---

### Property 1: Bundle SHA-256 integrity is self-consistent

*For any* `EvidenceBundle` constructed from arbitrary component verdict data, recomputing the SHA-256 hash over the canonical fields (excluding `sha256_hash` itself) must produce a value equal to the `sha256_hash` stored in the bundle.

**Validates: Requirements 1.3, 1.8**

---

### Property 2: Bundle structure invariant — all four components always present

*For any* `EvidenceBundle` built from any combination of invoked and non-invoked components, `component_verdicts` must contain exactly the keys `["BehavioralClassifier", "LegalRAG", "VisionForensics", "CurrencyVerifier"]`, and each non-invoked component's entry must have `verdict="not_applicable"`, `confidence=null`, `details=null`.

**Validates: Requirements 1.4, 1.6, 1.7**

---

### Property 3: Bundle hash invalidation on mutation

*For any* valid `EvidenceBundle`, mutating any evidence field (any key in `component_verdicts`, `chain_of_custody`, `analyzed_at`, or `case_id`) must cause `verify_hash()` to return `False`.

**Validates: Requirements 1.8**

---

### Property 4: JSON export round-trip preserves all bundle fields

*For any* `EvidenceBundle` with valid data, serialising it to JSON via `export_json()` and then deserialising the resulting file must produce an object equal to the original bundle (all fields preserved, types maintained, hash unchanged).

**Validates: Requirements 2.1, 2.2, 2.3**

---

### Property 5: Exported filename always matches naming convention

*For any* `bundle_id` string, the file produced by `export_json()` must be named `BK-{bundle_id}.evidence.json` and the file produced by `export_pdf()` must be named `BK-{bundle_id}.summary.pdf`.

**Validates: Requirements 2.4, 3.1**

---

### Property 6: Partial export survives component serialisation failure

*For any* `EvidenceBundle` where exactly one component's `details` field is replaced with an unserializable Python object, `export_json()` must:
(a) still produce a file (partial export),
(b) include all other three components' verdicts intact,
(c) add a `chain_of_custody` entry with `action` starting with `"serialisation_error:"`.

**Validates: Requirements 2.5**

---

### Property 7: PDF contains all required content sections

*For any* `EvidenceBundle`, the bytes of the generated PDF (extracted as text) must contain: the `bundle_id`, each of the four component names, the `sha256_hash`, and the disclaimer phrase "automated forensic estimate".

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

---

### Property 8: Metrics computation is arithmetically correct

*For any* list of `(ground_truth, predicted)` string pairs where values are drawn from `{"scam", "legit"}`, `EvaluationPipeline.compute_metrics()` must satisfy:
- `precision = tp / (tp + fp)` (or 0 when denominator is 0)
- `recall = tp / (tp + fn)` (or 0 when denominator is 0)
- `fpr = fp / (fp + tn)` (or 0 when denominator is 0)
- `f1 = 2 * precision * recall / (precision + recall)` (or 0 when denominator is 0)

**Validates: Requirements 7.2, 12.1**

---

### Property 9: Pipeline result count matches manifest sample count minus errors

*For any* `EvalManifest` with `n` transcript samples and `k` fault-injected samples (components that raise exceptions), the pipeline must produce exactly `n - k` valid metric-contributing results and exactly `k` eval_error entries.

**Validates: Requirements 7.1, 7.6**

---

### Property 10: Delta report shows correct arithmetic differences

*For any* two `EvalRunResult` objects with the same set of component keys, `EvaluationPipeline.delta(run_a, run_b)` must return per-metric differences where `delta[component][metric] == run_b.per_component[component][metric] - run_a.per_component[component][metric]`, accurate to floating-point precision.

**Validates: Requirements 7.4**

---

### Property 11: New pipeline predictions are consistent with existing EvaluationFramework

*For any* transcript sample, the prediction produced by `EvaluationPipeline` using the same threshold logic (`risk_score > 60 OR myths_found OR violations`) must equal the prediction produced by the existing `EvaluationFramework.run_eval()` for the same input.

**Validates: Requirements 7.5**

---

### Property 12: CIGate exits non-zero for any below-threshold metric combination

*For any* `EvalRunResult` where at least one component has a metric below its defined threshold (BehavioralClassifier precision < 0.85, or FPR > 0.10, or LegalRAG precision < 0.80, or VisionForensics precision < 0.75, or CurrencyVerifier precision < 0.75), the CIGate check function must return a non-zero exit code.

*For any* `EvalRunResult` where all components meet or exceed all thresholds, the CIGate check function must return exit code 0.

**Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.6**

---

### Property 13: CIGate skips threshold check when sample_count < 10

*For any* `EvalRunResult` where a component's `sample_count < 10`, the CIGate must not trigger a failure for that component even if its precision is 0.0.

**Validates: Requirements 9.8**

---

### Property 14: Unverified KB entries always carry the disclaimer annotation

*For any* `LegalClaim` produced from a KB entry where `bns_verified == false`, the `disclaimer` field of that claim must equal `"Citation not yet verified against current BNS/BNSS statute — treat as informational"`.

**Validates: Requirements 10.2, 10.3**

---

## Error Handling

### EvidenceExporter Error Hierarchy

```
EvidenceExportError           # base for all exporter errors
├── HashComputationError      # failed to serialise bundle for hashing
├── JsonWriteError            # filesystem failure during primary write
├── PdfGenerationError        # reportlab error during PDF creation
└── FallbackWriteError        # even the failure log write failed (logged to stderr only)
```

| Failure Scenario | Behaviour |
|---|---|
| One component verdict is not JSON-serialisable | Log `serialisation_error` in chain_of_custody; write partial export with remaining components; return path |
| Primary JSON write fails (disk full, permissions) | Attempt plain-text fallback to `evidence_export_failures.log`; raise `JsonWriteError` |
| Fallback write also fails | Log to stderr; raise `FallbackWriteError`; do not crash the FastAPI request thread |
| PDF generation fails | Log warning; `pdf_url` in API response returns `null`; JSON export is unaffected |
| Hash mismatch on verification | Return `{"verified": false, "bundle_id": "..."}` — do not raise an exception |

### EvaluationPipeline Error Handling

| Failure Scenario | Behaviour |
|---|---|
| Sample file path does not exist | Log warning; skip sample; do not increment error count |
| Component raises exception on a sample | Record in `eval_errors`; exclude from metric calculation; continue |
| Manifest file not found | Raise `FileNotFoundError` with a descriptive message |
| Git SHA unavailable (no git) | Use `"unknown"` as the commit SHA |

### CIGate Error Handling

| Failure Scenario | Behaviour |
|---|---|
| `GOOGLE_API_KEY` not set | Print error and `sys.exit(2)` (distinct from threshold failure exit code 1) |
| EvalManifest missing | Print error and `sys.exit(2)` |
| Component sample_count < 10 | Print `WARNING: insufficient data for <component>; skipping gate` |

---

## Testing Strategy

### Dual Testing Approach

Both unit/example-based tests and property-based tests are used. They are complementary:
- **Property tests** (Hypothesis, ≥100 iterations each) cover universal invariants across arbitrary inputs
- **Unit/example tests** cover specific edge cases, integration points, and error paths

### Property Tests (Hypothesis)

Stored in `backend/tests/test_evidence_exporter.py`, `test_eval_pipeline.py`, `test_ci_gate.py`.

Each property test is annotated with:
```python
# Feature: bharat-kavach-phase1, Property N: <property title>
@given(...)
@settings(max_examples=100)
def test_property_n_<title>(...):
    ...
```

Generators needed:
- `st.builds(EvidenceBundle, ...)` — arbitrary bundles with all four components present/absent
- `st.lists(st.tuples(st.sampled_from(["scam","legit"]), st.sampled_from(["scam","legit"])))` — for metrics testing
- `st.floats(min_value=0.0, max_value=1.0)` — for threshold testing in CIGate
- `st.text(min_size=1)` — for transcript content variation

### Unit/Example Tests

| Test file | What it covers |
|---|---|
| `test_evidence_exporter.py` | Dual-path fallback with mocked filesystem failures (Req 2.6), PDF content spot-checks, 404 behaviour |
| `test_eval_pipeline.py` | Missing file skip-and-warn, pipeline stdout table output, delta report with known values |
| `test_ci_gate.py` | Exit code 2 on missing env vars, insufficient-data warning message |
| `test_legal_rag.py` | `bns_verified=false` disclaimer annotation with known KB fixture |

### Integration Tests

Run with `pytest -m integration` (requires `GOOGLE_API_KEY`):
- End-to-end: POST `/analyze` with a scam transcript → GET `/cases/{id}/evidence` → verify bundle fields → GET `/cases/{id}/evidence/download` → verify PDF bytes non-empty
- EvalResultStore: two sequential `pipeline.run()` calls → verify two distinct files exist and neither overwrites the other

### What is NOT tested with property-based tests

- AWS/external service behaviour (no external services in Phase 1)
- PDF visual layout/readability (use example-based spot-check on extracted text)
- Actual AI engine accuracy (tested by EvaluationPipeline integration, not PBT)
- Filesystem concurrency (out of scope for hackathon phase)

### Note on networkx

`networkx` is listed as a dependency to note for future fraud-network graph work but is **not used in Phase 1**. No tests are written for it in this phase.
