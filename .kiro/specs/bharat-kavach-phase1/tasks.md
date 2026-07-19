# Implementation Plan: Bharat Kavach Phase 1

## Overview

Phase 1 adds four strictly-additive capabilities to the existing backend: auditable evidence export, a labeled evaluation dataset, a batch evaluation pipeline, and a CI quality gate. All work is in Python. The existing AI engines (`BehavioralClassifier`, `LegalRAG`, `VisionForensics`, `CurrencyVerifier`) are not modified — Phase 1 only wraps their outputs, seeds test data, and adds measurement infrastructure.

Implementation language: **Python** (matching the existing backend).

---

## Tasks

- [x] 1. Scaffold directories and update requirements
  - Create `backend/data/evidence_exports/` with a `.gitkeep` placeholder
  - Create `backend/data/eval_results/` with a `.gitkeep` placeholder
  - Create `backend/data/test_assets/transcripts/`, `backend/data/test_assets/documents/`, `backend/data/test_assets/currency/` with `.gitkeep` files
  - Create `backend/logs/` with a `.gitkeep` placeholder
  - Create `backend/scripts/` directory with an empty `__init__.py`
  - Create `backend/schemas/` directory
  - Add `reportlab==4.2.5` to `backend/requirements.txt`
  - _Requirements: 2.4, 3.1, 9.7_

- [x] 2. Define JSON Schema and Pydantic models for EvidenceBundle
  - [x] 2.1 Create `backend/schemas/evidence_bundle.schema.json`
    - Write a JSON Schema (draft-07) covering all fields from the EvidenceBundle design: `bundle_id` (UUID string), `analyzed_at` (ISO 8601 string), `case_id` (integer), `sha256_hash` (hex string), `model_registry` (object), `chain_of_custody` (array of step objects), `component_verdicts` (object with four fixed keys)
    - Mark all top-level fields as required
    - Constrain `confidence` to `[0.0, 1.0]` with nullable type
    - Constrain `artifact_type` to the enum `["transcript", "document_image", "currency_image"]`
    - _Requirements: 2.2, 2.3_

  - [x] 2.2 Add Pydantic models to `backend/services/evidence_exporter.py` (create file)
    - Define `ChainOfCustodyEntry`, `ComponentVerdict`, and `EvidenceBundle` exactly as specified in the design's Data Models section
    - Add `EvidenceExportError`, `HashComputationError`, `JsonWriteError`, `PdfGenerationError`, `FallbackWriteError` exception classes
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

- [x] 3. Implement `EvidenceExporter` core methods
  - [x] 3.1 Implement `build_bundle()`
    - Accept `case_id`, `transcript`, `behavioral_result`, `legal_findings`, `vision_result`, `currency_result`, `model_registry`
    - Generate UUID v4 for `bundle_id`; set `analyzed_at` to current UTC ISO 8601 timestamp
    - Map each AI engine result to a `ComponentVerdict`; use `{"verdict": "not_applicable", "confidence": null, "details": null}` for any `None` input
    - Build `chain_of_custody` list in invocation order, one entry per invoked component
    - Call `compute_hash()` and set `sha256_hash` on the bundle before returning
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 3.2 Implement `compute_hash()` and `verify_hash()`
    - `compute_hash`: build payload dict from all fields **except** `sha256_hash`; serialize with `json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)`; return SHA-256 hex digest of the UTF-8-encoded string
    - `verify_hash`: recompute hash and compare to `bundle.sha256_hash`; return `True`/`False`
    - _Requirements: 1.3, 1.8_

  - [x] 3.3 Write property test for Property 1 (hash self-consistency) in `backend/tests/test_evidence_exporter.py`
    - **Property 1: Bundle SHA-256 integrity is self-consistent**
    - Use `@given(st.builds(EvidenceBundle, ...))` to construct arbitrary bundles; assert `compute_hash(bundle) == bundle.sha256_hash`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 1: Bundle SHA-256 integrity is self-consistent`
    - **Validates: Requirements 1.3, 1.8**

  - [x] 3.4 Write property test for Property 3 (hash invalidation on mutation) in `backend/tests/test_evidence_exporter.py`
    - **Property 3: Bundle hash invalidation on mutation**
    - Generate a valid bundle; mutate one of `component_verdicts`, `chain_of_custody`, `analyzed_at`, or `case_id`; assert `verify_hash()` returns `False`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 3: Bundle hash invalidation on mutation`
    - **Validates: Requirements 1.8**

- [x] 4. Implement `EvidenceExporter.export_json()` with dual-path failure
  - [x] 4.1 Implement `export_json()`
    - Serialize `EvidenceBundle` to JSON; write to `EXPORTS_DIR/BK-{bundle_id}.evidence.json`
    - On component serialisation error: append a `chain_of_custody` entry with `action = "serialisation_error: {ExceptionType}"`; write partial export with remaining components intact; return path
    - On filesystem write failure: attempt plain-text append to `FAILURE_LOG` in format `"FAILURE|{bundle_id}|{timestamp}|{exception_type}|{exception_msg}\n"`; if fallback also fails, log to stderr; raise `JsonWriteError`
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_

  - [ ] 4.2 Write property test for Property 4 (JSON round-trip) in `backend/tests/test_evidence_exporter.py`
    - **Property 4: JSON export round-trip preserves all bundle fields**
    - Serialize via `export_json()` then deserialise the file; assert field equality including hash
    - Annotate: `# Feature: bharat-kavach-phase1, Property 4: JSON export round-trip preserves all bundle fields`
    - **Validates: Requirements 2.1, 2.2, 2.3**

  - [ ] 4.3 Write property test for Property 5 (filename convention) in `backend/tests/test_evidence_exporter.py`
    - **Property 5: Exported filename always matches naming convention**
    - For any `bundle_id`, assert `export_json()` output filename equals `BK-{bundle_id}.evidence.json` and `export_pdf()` output filename equals `BK-{bundle_id}.summary.pdf`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 5: Exported filename always matches naming convention`
    - **Validates: Requirements 2.4, 3.1**

  - [ ] 4.4 Write property test for Property 6 (partial export on serialisation failure) in `backend/tests/test_evidence_exporter.py`
    - **Property 6: Partial export survives component serialisation failure**
    - Inject an unserializable object into exactly one component's `details`; assert: (a) a file is still produced, (b) the other three components' verdicts are intact, (c) `chain_of_custody` contains an entry whose `action` starts with `"serialisation_error:"`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 6: Partial export survives component serialisation failure`
    - **Validates: Requirements 2.5**

- [x] 5. Implement `EvidenceExporter.export_pdf()` using reportlab
  - [x] 5.1 Implement `export_pdf()`
    - Use `reportlab.platypus.SimpleDocTemplate`; produce `EXPORTS_DIR/BK-{bundle_id}.summary.pdf`
    - Sections in order: Header (title + bundle_id + case_id), Analysis Timestamp, Component Verdicts Table (4 rows; `not_applicable` rows show `—` in Verdict and Confidence), Chain of Custody Timeline, SHA-256 Integrity Footer, Disclaimer
    - Disclaimer text: `"This document is an automated forensic estimate generated by Bharat Kavach AI. It does not constitute legal advice, a certified forensic examination report, or an official government document."`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x]* 5.2 Write property test for Property 7 (PDF required content) in `backend/tests/test_evidence_exporter.py`
    - **Property 7: PDF contains all required content sections**
    - Generate a PDF for an arbitrary bundle; extract text bytes; assert the text contains: `bundle_id`, each of the four component names, `sha256_hash`, and the phrase `"automated forensic estimate"`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 7: PDF contains all required content sections`
    - **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

  - [x]* 5.3 Write property test for Property 2 (all-four-components invariant) in `backend/tests/test_evidence_exporter.py`
    - **Property 2: Bundle structure invariant — all four components always present**
    - For any combination of invoked/non-invoked components, assert `component_verdicts` has exactly the four keys `["BehavioralClassifier", "LegalRAG", "VisionForensics", "CurrencyVerifier"]` and non-invoked entries have `verdict="not_applicable"`, `confidence=null`, `details=null`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 2: Bundle structure invariant — all four components always present`
    - **Validates: Requirements 1.4, 1.6, 1.7**

- [x] 6. Checkpoint — evidence exporter complete
  - Ensure all tests in `backend/tests/test_evidence_exporter.py` pass. Ask the user if questions arise.

- [x] 7. Expand Legal KB and update LegalRAG
  - [x] 7.1 Expand `backend/data/legal_kb.json` to 10+ entries
    - Add `bns_verified` boolean field to every existing entry — **default to `false` until human review is complete; do NOT set `bns_verified: true` without completing the checklist below**
    - Add `verified_by` (string, nullable — name/initials of the person who cross-checked) and `verified_date` (ISO 8601 date string, nullable) fields alongside `bns_verified` on every entry
    - Add five new entries as specified in the design: `aadhaar_misuse_myth_1`, `ncrb_ip_myth_1`, `bank_freeze_myth_1`, `drug_parcel_myth_1`, `secret_case_myth_1` — each initially with `bns_verified: false`, `verified_by: null`, `verified_date: null`
    - Ensure no IPC or CrPC section numbers appear anywhere in the file
    - **⚠️ HUMAN REVIEW REQUIRED — before setting `bns_verified: true` on any entry:** cross-check the cited BNS/BNSS section number against the official gazette text published by the Ministry of Law and Justice (available at legislative.gov.in or indiacode.nic.in); confirm the section number, title, and scope match the claim pattern; then set `bns_verified: true`, `verified_by: "<your name>"`, `verified_date: "<YYYY-MM-DD>"`. Do not merge entries with `bns_verified: true` that have not completed this manual step.
    - _Requirements: 10.1, 10.2, 10.4_

  - [x] 7.2 Update `LegalRAG.verify_legal_claims()` in `backend/ai_engines/legal_rag.py` for `bns_verified` annotation
    - When a matched KB entry has `bns_verified == false`, set `LegalClaim.disclaimer` to `"Citation not yet verified against current BNS/BNSS statute — treat as informational"`
    - Leave default disclaimer unchanged for `bns_verified == true` entries
    - _Requirements: 10.2, 10.3_

  - [x]* 7.3 Write property test for Property 14 (unverified KB disclaimer) in `backend/tests/test_legal_rag.py` (add to existing file)
    - **Property 14: Unverified KB entries always carry the disclaimer annotation**
    - For any `LegalClaim` produced from a KB entry where `bns_verified == false`, assert `claim.disclaimer == "Citation not yet verified against current BNS/BNSS statute — treat as informational"`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 14: Unverified KB entries always carry the disclaimer annotation`
    - **Validates: Requirements 10.2, 10.3**

- [x] 8. Create EvalManifest with bootstrap seed data
  - [x] 8.1 Create `backend/data/eval_manifest.json` with schema structure and initial seed entries
    - Set `manifest_version: 1`, `created_at`, and `description`
    - Add at least 10 transcript entries with `ground_truth: "scam"` (covering FedEx-parcel, digital-arrest, ED/CBI impersonation, OTP-capture, Aadhaar-misuse, drug-parcel, UPI-threat, TRAI-notice, court-summons, arrest-warrant patterns); each with a `source_citation` pointing to an MHA advisory or documented case
    - Add at least 10 transcript entries with `ground_truth: "legit"` (covering bank transaction notification, OTP delivery, service booking confirmation, personal conversation, RBI advisory genuine call, legal consultation, court clerk, police official non-threatening, customer support, government welfare notification); include at least 3 that are `tricky_negative: true` (contain "CBI", "warrant", "FIR", "ED", or "arrest" in a non-scam context)
    - Add at least 2 placeholder document image entries with `ground_truth: "authentic"` and at least 2 with `ground_truth: "forged"` (file_paths pointing to `documents/` subdirectory; mark with a comment that actual images require manual collection)
    - Add at least 2 placeholder currency image entries with `ground_truth: "genuine"` and at least 2 with `ground_truth: "counterfeit"` (file_paths pointing to `currency/` subdirectory; `denomination` field set)
    - **⚠️ This task delivers the schema-valid structure and a ~20-sample bootstrap set only. The CI gate (task 11) will print `WARNING: insufficient data; skipping gate` for VisionForensics and CurrencyVerifier until real image samples are collected. Do not mistake a skipped gate for a passing gate.**
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 8.5 Manual Data Collection Sprint (BLOCKS CI gate from being meaningful)
  - **This task must be completed before any metrics cited in the pitch deck are considered credible. The CI gate will print `WARNING: insufficient data; skipping gate` for all components until `sample_count >= 10` per component.**
  - Transcript corpus — target 200+ total (100 scam + 100 legit):
    - Scambaiting archives: r/scams, youtube scambaiter channels (Jim Browning, Kitboga — transcripts from published videos), Scam Alert India blog
    - MHA advisories: mha.gov.in/en/commoncontent/cyber-crime → download published digital-arrest case summaries
    - News coverage: The Hindu, Times of India, NDTV Cyber Crime reports citing specific scam call transcripts
    - Each entry must have `source_citation` with a verifiable URL — no fabricated or LLM-generated transcripts
  - Document image corpus — target 50+ (25 authentic + 25 forged):
    - Forged: cybercrime.gov.in case evidence disclosures, scambaiting archive exhibits, MHA-published sample fake warrants
    - Authentic: public domain court summons/notices from disclosed case records, government gazette samples
    - Never create new forgery artifacts — only use existing sourced examples
  - Currency image corpus — target 50+ across ₹100/₹200/₹500/₹2000 (25 genuine + 25 counterfeit):
    - Check Kaggle: search "Indian currency fake detection", "FICN dataset", "Indian rupee counterfeit"
    - Record dataset name, version, and URL in `source_citation` for every Kaggle entry
    - RBI Annual Report 2025 FICN chapter for context on available seizure samples
  - After collection: increment `manifest_version` and re-run the CI gate to get real metrics
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 6.1, 6.2, 6.3_

- [x] 9. Implement `EvaluationPipeline` and `EvalResultStore`
  - [x] 9.1 Create `backend/services/eval_pipeline.py` with dataclasses
    - Define `ComponentMetrics` and `EvalRunResult` dataclasses exactly as in the design's Data Models section
    - _Requirements: 7.2, 7.3, 8.1, 8.2, 8.3, 8.4_

  - [x] 9.2 Implement `EvalResultStore` class
    - `save(run_result)`: serialize to JSON and write to `RESULTS_DIR/eval_{git_sha}_{ts}.json` using filesystem-safe timestamp (`:` replaced by `-`); never overwrite existing files
    - `load(run_id)`: deserialize result file by run_id
    - `list_runs()`: return all run_ids sorted ascending by timestamp
    - _Requirements: 7.3, 8.1, 8.4_

  - [x] 9.3 Implement `EvaluationPipeline` class
    - `__init__`: instantiate all four AI engines and `EvaluationFramework`; accept `api_key` and optional `manifest_path`
    - `load_manifest(path)`: load and validate EvalManifest JSON; raise `FileNotFoundError` with descriptive message on missing file
    - `compute_metrics(results)`: compute precision, recall, F1, FPR using the same formula as `EvaluationFramework.calculate_metrics()`; handle zero-denominator cases by returning 0
    - `delta(run_a, run_b)`: return per-metric arithmetic differences for all shared component keys
    - _Requirements: 7.1, 7.2, 7.4, 7.5_

  - [x] 9.4 Implement `EvaluationPipeline.run()`
    - For each sample in `manifest["samples"]`: skip (log warning) if file_path is absent; run through `applicable_components`; on component exception, record in `eval_errors`, exclude from metrics, continue
    - Use existing threshold logic: predict `"scam"` when `risk_score > 60 OR any LegalClaim.verdict == "confirmed_false" OR protocol_violations found`
    - Retrieve git commit SHA via `subprocess`; fall back to `"unknown"` if unavailable
    - Print per-component summary table to stdout on completion
    - Save result via `EvalResultStore`
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6, 7.7, 8.2, 8.3_

  - [x]* 9.5 Write property test for Property 8 (metrics arithmetic) in `backend/tests/test_eval_pipeline.py`
    - **Property 8: Metrics computation is arithmetically correct**
    - Generate arbitrary lists of `(ground_truth, predicted)` pairs from `{"scam", "legit"}`; assert precision, recall, F1, FPR satisfy the exact formulas with zero-denominator handling
    - Annotate: `# Feature: bharat-kavach-phase1, Property 8: Metrics computation is arithmetically correct`
    - **Validates: Requirements 7.2, 12.1**

  - [x]* 9.6 Write property test for Property 9 (result count = manifest count minus errors) in `backend/tests/test_eval_pipeline.py`
    - **Property 9: Pipeline result count matches manifest sample count minus errors**
    - Construct an EvalManifest with `n` transcript samples and `k` fault-injected components; assert valid results count equals `n - k` and `eval_errors` count equals `k`
    - Annotate: `# Feature: bharat-kavach-phase1, Property 9: Pipeline result count matches manifest sample count minus errors`
    - **Validates: Requirements 7.1, 7.6**

  - [x]* 9.7 Write property test for Property 10 (delta arithmetic) in `backend/tests/test_eval_pipeline.py`
    - **Property 10: Delta report shows correct arithmetic differences**
    - Generate two `EvalRunResult` objects with the same component keys and arbitrary metric floats; assert `delta[c][m] == run_b.per_component[c][m] - run_a.per_component[c][m]` for all components and metrics
    - Annotate: `# Feature: bharat-kavach-phase1, Property 10: Delta report shows correct arithmetic differences`
    - **Validates: Requirements 7.4**

  - [x]* 9.8 Write property test for Property 11 (pipeline consistent with EvaluationFramework) in `backend/tests/test_eval_pipeline.py`
    - **Property 11: New pipeline predictions are consistent with existing EvaluationFramework**
    - For arbitrary transcript samples, assert `EvaluationPipeline` and `EvaluationFramework.run_eval()` produce the same prediction using the same threshold logic
    - Annotate: `# Feature: bharat-kavach-phase1, Property 11: New pipeline predictions are consistent with existing EvaluationFramework`
    - **Validates: Requirements 7.5**

- [x] 10. Checkpoint — evaluation pipeline complete
  - Ensure all tests in `backend/tests/test_eval_pipeline.py` pass. Ask the user if questions arise.

- [x] 11. Implement `CIGate` script
  - [x] 11.1 Create `backend/scripts/ci_eval.py`
    - Step 1: load `GOOGLE_API_KEY` from env; if missing, print error and `sys.exit(2)`
    - Step 2: load `backend/data/eval_manifest.json`; if missing, print error and `sys.exit(2)`
    - Step 3: instantiate `EvaluationPipeline`; call `pipeline.run(manifest)`; save via `EvalResultStore`
    - Step 4: for each component — if `sample_count < 10`, print `"WARNING: insufficient data for <component>; skipping gate"` and skip; else compare against THRESHOLDS table from design
    - Step 5: if any failures, print failure details and `sys.exit(1)`; else print PASS summary table in the format defined in the design and `sys.exit(0)`
    - Script must be executable (`if __name__ == "__main__": main()`) with no imports from `main.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [x]* 11.2 Write property test for Property 12 (non-zero exit on below-threshold metrics) in `backend/tests/test_ci_gate.py`
    - **Property 12: CIGate exits non-zero for any below-threshold metric combination**
    - Generate `EvalRunResult` objects where at least one component metric is below its threshold; assert the CIGate check returns non-zero. Also generate all-passing results and assert exit code 0
    - Annotate: `# Feature: bharat-kavach-phase1, Property 12: CIGate exits non-zero for any below-threshold metric combination`
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.6**

  - [ ] 11.3 Write property test for Property 13 (insufficient-data skips threshold) in `backend/tests/test_ci_gate.py`
    - **Property 13: CIGate skips threshold check when sample_count < 10**
    - For any component with `sample_count < 10` (even with `precision == 0.0`), assert the CIGate does not trigger a failure for that component
    - Annotate: `# Feature: bharat-kavach-phase1, Property 13: CIGate skips threshold check when sample_count < 10`
    - **Validates: Requirements 9.8**

- [x] 12. Add FastAPI evidence endpoints to `backend/main.py`
  - [x] 12.1 Add `GET /cases/{case_id}/evidence` endpoint
    - Query `CaseReport` by `case_id`; return HTTP 404 with `"Case not found"` if absent
    - Call `exporter.get_or_create_bundle(case)` (implement this method on `EvidenceExporter`: load cached `.evidence.json` if it exists, otherwise call `build_bundle()` + `export_json()` + `export_pdf()`)
    - Return bundle fields as JSON plus a `pdf_url` field set to `f"/cases/{case_id}/evidence/download"`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [x] 12.2 Add `GET /cases/{case_id}/evidence/download` endpoint
    - Query `CaseReport` by `case_id`; return HTTP 404 with `"Case not found"` if absent
    - Resolve PDF path via `exporter.get_pdf_path(case.bundle_id)`; return HTTP 404 with `"PDF not yet generated for this case"` if file does not exist
    - Return `FileResponse` with `media_type="application/pdf"` and `Content-Disposition: attachment; filename="BK-{bundle_id}.summary.pdf"`
    - _Requirements: 11.3, 11.4, 11.5_

- [x] 13. Final checkpoint — full Phase 1 complete
  - Ensure all property tests (`test_evidence_exporter.py`, `test_eval_pipeline.py`, `test_ci_gate.py`) and any affected existing tests pass.
  - Verify `backend/schemas/evidence_bundle.schema.json` is present and valid JSON.
  - Verify `backend/data/eval_manifest.json` has `manifest_version`, `samples` with at least 20 transcript entries and the required fields.
  - Verify `backend/data/legal_kb.json` has 10+ entries, every entry has `bns_verified` + `verified_by` + `verified_date` fields, and no IPC/CrPC references remain.
  - **Verify git SHA capture:** run `git rev-parse --short HEAD` from the backend directory and confirm it returns a real commit SHA (not `"unknown"`) — if it returns `"unknown"`, git is not configured in this environment and any metrics cited externally will have an unauditable run_id. Fix before citing any numbers in the pitch deck.
  - **Verify CI gate is actually gating:** check that `sample_count >= 10` for at least BehavioralClassifier and LegalRAG before calling the gate meaningful. If the gate prints only `WARNING: insufficient data` lines for all components, task 8.5 (Manual Data Collection Sprint) has not been completed — do not cite CI gate results in the pitch deck until real data is in.
  - Ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP iteration.
- Each task references specific requirements for traceability.
- **Task 8.5 (Manual Data Collection Sprint) is not optional for pitch deck credibility** — the CI gate silently skips threshold checks when `sample_count < 10`, so it cannot gate anything meaningful until real data is collected. Do not modify Requirement 9.8's insufficient-data threshold to work around this; the fix is more real data, not a lower bar.
- **`bns_verified: true` requires human review** — do not set this flag without cross-checking the cited section number against the official BNS/BNSS gazette at legislative.gov.in or indiacode.nic.in. Use the `verified_by` and `verified_date` fields to record who verified and when.
- **git SHA in EvalResultStore** — if `git rev-parse --short HEAD` returns nothing (git not configured), run IDs will contain `"unknown"` which undercuts the auditability story. Verify git is available in your runtime environment before citing any run_id-backed metrics externally.
- Property tests use Hypothesis (already present in `.hypothesis/`); annotate each with `# Feature: bharat-kavach-phase1, Property N: <title>` and `@settings(max_examples=100)`.
- `reportlab` must be pinned to a specific version to avoid PDF layout regressions between versions.
- The `EvidenceExporter` must never import from `main.py` and must never call any AI engine directly.
- `ci_eval.py` must be a standalone script with no imports from `main.py`.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["3.1", "3.2", "8.1"] },
    { "id": 3, "tasks": ["3.3", "3.4", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "7.1", "9.1"] },
    { "id": 6, "tasks": ["7.2", "9.2", "9.3"] },
    { "id": 7, "tasks": ["7.3", "9.4"] },
    { "id": 8, "tasks": ["9.5", "9.6", "9.7", "9.8", "11.1"] },
    { "id": 9, "tasks": ["11.2", "11.3", "12.1"] },
    { "id": 10, "tasks": ["12.2"] },
    { "id": 11, "tasks": ["8.5"] }
  ]
}
```

**Note on task 8.5:** It is placed in wave 11 (last) because it is manual work that can proceed in parallel with coding waves, but it must complete before the CI gate (task 11) produces any meaningful pass/fail results. Tasks 1–12 can all be executed by the agent; task 8.5 requires human researchers sourcing real data.
