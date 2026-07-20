# Requirements Document

## Introduction

Bharat Kavach Phase 1 establishes the **validation infrastructure and evidence-quality foundation** that all subsequent phases depend on. The existing system has four working AI components — BehavioralClassifier, LegalRAG, VisionForensics, and CurrencyVerifier — but currently lacks auditable evidence export, a curated labeled test dataset, a systematic evaluation pipeline, and automated CI quality gates.

This phase upgrades those gaps in four areas:

1. **Auditable Evidence Export Schema** — every AI verdict becomes legally admissible, with cryptographic hash, timestamp, model provenance, chain-of-custody, and signed PDF summary.
2. **Test Dataset Collection & Management** — a cited, labeled, versioned corpus of real scam transcripts, forged documents, and currency images.
3. **Batch Evaluation Pipeline** — automated per-component precision/recall/F1/FPR computation against that dataset.
4. **CI Evaluation Trigger** — a script that gates every commit on minimum accuracy thresholds.

Nothing here replaces existing architecture. All work extends or wraps the existing `BehavioralClassifier`, `LegalRAG`, `VisionForensics`, `CurrencyVerifier`, `EvaluationFramework`, and FastAPI backend.

---

## Glossary

- **EvidenceBundle**: The complete structured record produced by one full analysis run — containing inputs, all component verdicts, metadata, and integrity fields.
- **ChainOfCustody**: An ordered log recording which component processed what artifact, in what sequence, and at what time within a single analysis run.
- **EvidenceExporter**: The new module responsible for serialising an EvidenceBundle to signed JSON and generating the PDF summary.
- **EvalManifest**: The versioned YAML/JSON file that declares the test dataset: each sample's source citation, ground-truth label, file path, and applicable components.
- **EvaluationPipeline**: The extended evaluation harness that runs all four AI components against the EvalManifest and computes per-component metrics.
- **EvalResultStore**: The versioned storage location (file-based, keyed by git commit SHA and timestamp) where each EvaluationPipeline run persists its output metrics.
- **CIGate**: The CI script that invokes the EvaluationPipeline and produces a pass/fail outcome based on minimum threshold checks.
- **BehavioralClassifier**: Existing Gemini-powered 6-stage scam arc classifier in `backend/ai_engines/behavioral.py`.
- **LegalRAG**: Existing hybrid knowledge-base legal claim verifier in `backend/ai_engines/legal_rag.py`.
- **VisionForensics**: Existing OpenCV + Gemini Vision ensemble document forensics engine in `backend/ai_engines/vision.py`.
- **CurrencyVerifier**: Existing ROI-based currency analysis module in `backend/ai_engines/currency.py`. Currently ₹500-only.
- **BNS**: Bharatiya Nyaya Sanhita — replaced IPC effective July 1, 2024.
- **BNSS**: Bharatiya Nagarik Suraksha Sanhita — replaced CrPC effective July 1, 2024.
- **FPR**: False Positive Rate — the fraction of legitimate (non-scam) inputs incorrectly flagged as threats.
- **F1**: Harmonic mean of precision and recall.
- **SHA-256**: The cryptographic hash algorithm used for evidence integrity verification.

---

## Requirements

---

### Requirement 1: Auditable Evidence Bundle Schema

**User Story:** As a law enforcement officer, I want every AI verdict produced by Bharat Kavach to include cryptographic integrity proof, model provenance, and chain-of-custody, so that the evidence package can be submitted to court without challenge on authenticity or reproducibility grounds.

#### Acceptance Criteria

1. THE EvidenceBundle SHALL contain a `bundle_id` field that is a UUID v4 uniquely identifying each analysis run.
2. THE EvidenceBundle SHALL contain an `analyzed_at` field in ISO 8601 format with UTC timezone (e.g., `2026-01-15T10:30:00Z`).
3. THE EvidenceBundle SHALL contain a `sha256_hash` field that is the SHA-256 hex digest of the canonical JSON serialisation of all evidence fields excluding the `sha256_hash` field itself.
4. THE EvidenceBundle SHALL contain a `model_registry` field — a mapping from each component name (`BehavioralClassifier`, `LegalRAG`, `VisionForensics`, `CurrencyVerifier`) to the model identifier string used during that analysis run.
5. THE EvidenceBundle SHALL contain a `chain_of_custody` field — an ordered list of entries, where each entry records: `step` (integer), `component` (string), `artifact_type` (one of `transcript`, `document_image`, `currency_image`), `action` (string description), and `timestamp` (ISO 8601).
6. THE EvidenceBundle SHALL contain a `component_verdicts` field — an object with one sub-object per applicable component, each containing: `verdict` (string), `confidence` (float in [0.0, 1.0]), `details` (component-specific structured data).
7. WHEN a component is not invoked for a given analysis run (e.g., no image uploaded), THE EvidenceBundle SHALL record that component's entry in `component_verdicts` as `{"verdict": "not_applicable", "confidence": null, "details": null}`.
8. IF the `sha256_hash` in a stored EvidenceBundle does not match a recomputed hash of the same bundle's evidence fields, THEN THE EvidenceExporter SHALL return a verification failure status rather than an authenticity confirmation.

---

### Requirement 2: Signed JSON Export

**User Story:** As a cybercrime investigator, I want to export an EvidenceBundle as a machine-readable signed JSON file, so that I can ingest it into case management systems and verify it has not been tampered with after export.

#### Acceptance Criteria

1. WHEN an analysis run completes, THE EvidenceExporter SHALL produce a JSON file conforming to the EvidenceBundle schema defined in Requirement 1.
2. THE EvidenceExporter SHALL produce JSON output that is valid against a published JSON Schema (stored in the repository at `backend/schemas/evidence_bundle.schema.json`).
3. WHEN a consumer validates an exported JSON file against the published JSON Schema, THE EvidenceExporter SHALL ensure that validation passes without errors.
4. THE EvidenceExporter SHALL name exported files using the pattern `BK-{bundle_id}.evidence.json`.
5. IF the serialisation of any component's verdict raises an exception, THEN THE EvidenceExporter SHALL record the failure in the `chain_of_custody` log with an `action` value of `serialisation_error: {exception_type}` and SHALL still produce a partial export containing all successfully serialised components.
6. IF the EvidenceExporter is unable to write the partial export (e.g. disk/filesystem failure) AND unable to write to the `chain_of_custody` log, THEN THE EvidenceExporter SHALL fall back to writing a minimal failure record — `bundle_id`, `timestamp`, and raw exception details — to a separate, independent failure log (`backend/logs/evidence_export_failures.log`) that does not depend on the same write path as the primary export. The fallback write mechanism SHALL use plain-text append (not structured JSON write) so that whatever caused the primary failure (disk full, permissions, JSON serialisation bug) is less likely to also break the fallback.

---

### Requirement 3: PDF Summary Export

**User Story:** As a senior police officer reviewing a case, I want a human-readable PDF summary of the evidence bundle, so that I can assess findings without needing to parse JSON.

#### Acceptance Criteria

1. WHEN an EvidenceBundle is available, THE EvidenceExporter SHALL generate a PDF summary file named `BK-{bundle_id}.summary.pdf`.
2. THE PDF summary SHALL include: case reference (bundle_id), analysis timestamp, per-component verdict table with confidence scores, chain-of-custody timeline, and SHA-256 hash footer.
3. THE PDF summary SHALL include a disclaimer section stating that the document is an automated forensic estimate and does not constitute legal advice or a certified forensic examination report.
4. THE PDF summary SHALL display component names, verdict values, and confidence scores in a tabular layout readable without specialised software.
5. WHEN any component verdict is `not_applicable`, THE PDF summary SHALL display that component's row with `—` in the verdict and confidence columns rather than omitting the row.

---

### Requirement 4: Test Dataset — Scam Call Transcripts

**User Story:** As a data scientist validating the BehavioralClassifier and LegalRAG, I want a labeled corpus of at least 100 real scam transcripts and 100 real legitimate transcripts, so that I can compute unbiased precision and recall against genuinely representative samples.

#### Acceptance Criteria

1. THE EvalManifest SHALL contain at least 100 entries with `ground_truth: scam`, each sourced from publicly available scambaiting archives, MHA cybercrime advisories, or verified news coverage of "digital arrest" fraud cases.
2. THE EvalManifest SHALL contain at least 100 entries with `ground_truth: legit`, covering genuine call scenarios including transactional banking, service notifications, personal conversations, and legal/official communications.
3. THE EvalManifest SHALL contain at least 20 "tricky negative" entries — legitimate transcripts that contain terms such as "CBI", "warrant", "arrest", "ED", or "FIR" in a non-scam context — labeled `ground_truth: legit`.
4. WHEN a transcript entry is added to the EvalManifest, THE EvalManifest SHALL include a `source_citation` field containing a URL or MHA advisory reference for that entry.
5. THE EvalManifest SHALL never contain a transcript that was synthetically generated by an LLM as a primary fabrication of a scam or legitimate call — all transcripts must be sourced, adapted, or summarised from documented real-world incidents.
6. THE EvalManifest SHALL be stored as a versioned file under `backend/data/eval_manifest.json`, and WHEN it is modified, THE EvalManifest SHALL include a `manifest_version` field that is incremented with each change.

---

### Requirement 5: Test Dataset — Forged Documents

**User Story:** As a data scientist validating VisionForensics, I want a labeled set of at least 50 document pairs (real vs. forged), so that I can measure document forgery detection accuracy on authentic data.

#### Acceptance Criteria

1. THE EvalManifest SHALL contain at least 25 document image entries labeled `ground_truth: authentic` representing genuine Indian official documents (court summons, police notices, government letters) sourced from public domain, case records disclosed in news reporting, or court-released exhibits.
2. THE EvalManifest SHALL contain at least 25 document image entries labeled `ground_truth: forged` sourced from scambaiting archives, cybercrime case evidence disclosed in press releases, or MHA-published sample fake documents.
3. WHEN a document image entry is added to the EvalManifest, THE EvalManifest SHALL include a `source_citation` field with a verifiable URL or reference.
4. THE EvalManifest SHALL never include a document image that was digitally fabricated as a new forgery artifact for the purpose of this dataset — sourced evidence of pre-existing forgeries is permitted.
5. THE EvalManifest SHALL store document image paths relative to `backend/data/test_assets/documents/` and WHEN the referenced file is absent, THE EvaluationPipeline SHALL skip that entry and log a warning rather than raising an unhandled exception.

---

### Requirement 6: Test Dataset — Currency Images

**User Story:** As a data scientist extending CurrencyVerifier beyond ₹500, I want labeled currency image samples across ₹100, ₹200, ₹500, and ₹2000 denominations covering both genuine and counterfeit notes, so that I can measure detection accuracy per denomination.

#### Acceptance Criteria

1. THE EvalManifest SHALL contain at least 25 currency image entries labeled `ground_truth: genuine`, spanning at least two different denominations (₹500 and one other from ₹100, ₹200, ₹2000).
2. THE EvalManifest SHALL contain at least 25 currency image entries labeled `ground_truth: counterfeit`, sourced from Kaggle Indian currency datasets, RBI-published counterfeit note samples, or cybercrime case evidence — with source citations.
3. WHEN sourcing currency images from Kaggle, THE EvalManifest SHALL record the dataset name, version, and URL in the `source_citation` field for each entry.
4. THE EvalManifest SHALL never include a currency image that was digitally created as a new counterfeit note artifact — pre-existing samples from cited datasets are required.
5. THE EvalManifest SHALL store currency image paths relative to `backend/data/test_assets/currency/` and WHEN the referenced file is absent, THE EvaluationPipeline SHALL skip that entry and log a warning.

---

### Requirement 7: Batch Evaluation Pipeline

**User Story:** As an AI engineer, I want a batch evaluation pipeline that runs all four AI components against the full labeled test dataset and outputs per-component metrics, so that I can measure and track system accuracy week over week.

#### Acceptance Criteria

1. WHEN THE EvaluationPipeline is invoked, THE EvaluationPipeline SHALL load the EvalManifest and run each labeled sample through the applicable component(s): transcripts through BehavioralClassifier and LegalRAG, document images through VisionForensics, currency images through CurrencyVerifier.
2. WHEN THE EvaluationPipeline completes, THE EvaluationPipeline SHALL output per-component metrics including: precision, recall, F1 score, and false-positive rate, computed from the ground-truth labels in the EvalManifest.
3. THE EvaluationPipeline SHALL persist each run's metrics to the EvalResultStore as a JSON file named `eval_{git_commit_sha}_{iso_timestamp}.json` under `backend/data/eval_results/`.
4. WHEN two EvaluationPipeline result files exist in the EvalResultStore, THE EvaluationPipeline SHALL be able to produce a delta report showing the change in each metric between the two runs.
5. THE EvaluationPipeline SHALL process transcript samples using the same decision threshold logic as the existing `EvaluationFramework.run_eval()` method in `backend/tests/eval_metrics.py`, extended to support the larger manifest.
6. IF a component raises an exception while processing a sample, THEN THE EvaluationPipeline SHALL record that sample as an evaluation error, exclude it from metric calculations, and continue processing remaining samples.
7. WHEN THE EvaluationPipeline completes, THE EvaluationPipeline SHALL print a per-component summary table to stdout showing component name, sample count, precision, recall, F1, and FPR.

---

### Requirement 8: Metric Versioning and Traceability

**User Story:** As a hackathon presenter, I want every metric I cite in the pitch deck to trace directly to a specific EvalResultStore run output, so that judges can verify the numbers are from real measurements and not estimates.

#### Acceptance Criteria

1. THE EvalResultStore SHALL retain all historical result files, and WHEN a new run is appended, THE EvalResultStore SHALL not overwrite or delete any previous result file.
2. THE EvaluationPipeline SHALL record the `manifest_version` from the EvalManifest into the result file, so that the dataset version used to produce each metric is auditable.
3. THE EvaluationPipeline SHALL record the git commit SHA of the codebase at run time into the result file.
4. WHEN the result file is read, THE EvalResultStore SHALL expose a `run_id` field that is unique across all stored runs, composed of `{git_commit_sha}_{iso_timestamp}`.

---

### Requirement 9: CI Evaluation Gate

**User Story:** As a developer committing code changes to Bharat Kavach, I want a CI script that automatically runs the evaluation pipeline and fails the build if accuracy drops below defined thresholds, so that regressions in detection quality are caught before merge.

#### Acceptance Criteria

1. WHEN a CI-triggering event occurs (e.g., push to main or pull request), THE CIGate SHALL invoke THE EvaluationPipeline against the current EvalManifest and capture the resulting metrics.
2. WHEN THE EvaluationPipeline metrics show BehavioralClassifier precision below 0.85 or FPR above 0.10, THE CIGate SHALL exit with a non-zero status code indicating a failing build.
3. WHEN THE EvaluationPipeline metrics show LegalRAG precision below 0.80, THE CIGate SHALL exit with a non-zero status code.
4. WHEN THE EvaluationPipeline metrics show VisionForensics precision below 0.75, THE CIGate SHALL exit with a non-zero status code.
5. WHEN THE EvaluationPipeline metrics show CurrencyVerifier precision below 0.75, THE CIGate SHALL exit with a non-zero status code.
6. WHEN all threshold checks pass, THE CIGate SHALL exit with status code 0 and SHALL print a pass summary showing each component's precision and FPR against its threshold.
7. THE CIGate SHALL be implementable as a single executable script (`backend/scripts/ci_eval.py`) that requires no manual configuration beyond environment variables already defined in `.env`.
8. WHEN the EvalManifest contains fewer than 10 samples for a given component, THE CIGate SHALL print a warning indicating insufficient data for that component's gate, and SHALL skip that component's threshold check rather than failing.

---

### Requirement 10: Legal Knowledge Base Currency

**User Story:** As a legal analyst reviewing Bharat Kavach outputs, I want all legal citations in the system to reference BNS/BNSS sections (not IPC/CrPC), so that the system is correct for India's post-July 2024 legal framework.

#### Acceptance Criteria

1. THE LegalRAG knowledge base file (`backend/data/legal_kb.json`) SHALL contain only citations from Bharatiya Nyaya Sanhita (BNS) and Bharatiya Nagarik Suraksha Sanhita (BNSS) — no references to IPC or CrPC section numbers.
2. WHEN a new knowledge base entry is added, THE LegalRAG knowledge base entry SHALL include a `bns_verified` boolean field set to `true` only when the cited BNS/BNSS section has been manually verified against the current published statute text, a `verified_by` string field (nullable) recording the name or initials of the person who performed the verification, and a `verified_date` string field (nullable) in ISO 8601 date format recording the date of verification.
3. IF a knowledge base entry has `bns_verified: false`, THEN THE LegalRAG SHALL annotate that entry's output with a disclaimer: `"Citation not yet verified against current BNS/BNSS statute — treat as informational"`.
4. THE LegalRAG knowledge base SHALL contain at least 10 entries covering distinct digital arrest scam patterns, each with a verified BNS/BNSS provision.

---

### Requirement 11: Evidence Export API Endpoint

**User Story:** As a developer integrating Bharat Kavach into a case management system, I want a REST endpoint that returns both the signed JSON evidence bundle and a link to the PDF summary for a given case, so that downstream systems can retrieve legally formatted evidence programmatically.

#### Acceptance Criteria

1. THE FastAPI backend SHALL expose a `GET /cases/{case_id}/evidence` endpoint that accepts a valid integer `case_id`.
2. WHEN a valid `case_id` is provided, THE `GET /cases/{case_id}/evidence` endpoint SHALL return the EvidenceBundle JSON for that case, including all fields defined in Requirement 1.
3. WHEN a valid `case_id` is provided, THE `GET /cases/{case_id}/evidence` endpoint SHALL also return a `pdf_url` field pointing to the downloadable PDF summary for that case.
4. IF the provided `case_id` does not correspond to an existing case in the database, THEN THE `GET /cases/{case_id}/evidence` endpoint SHALL return HTTP 404 with an error message `"Case not found"`.
5. THE FastAPI backend SHALL expose a `GET /cases/{case_id}/evidence/download` endpoint that streams the PDF summary file as a `application/pdf` response with `Content-Disposition: attachment`.

---

### Requirement 12: False Positive Rate Constraint for Citizen-Facing Analysis

**User Story:** As a product manager concerned about user trust, I want the BehavioralClassifier to maintain a false positive rate below 10% on the labeled negative-control corpus, so that legitimate callers are not falsely alarmed.

#### Acceptance Criteria

1. WHEN THE BehavioralClassifier is evaluated against the EvalManifest entries labeled `ground_truth: legit`, THE EvaluationPipeline SHALL compute and record the FPR as `fp / (fp + tn)`.
2. WHEN THE EvaluationPipeline reports a BehavioralClassifier FPR above 0.10, THE CIGate SHALL trigger a build failure as specified in Requirement 9.2.
3. THE EvalManifest SHALL include at least 20 tricky-negative samples (as defined in Requirement 4.3) so that the FPR measurement is sensitive to the most common false-positive failure mode — legitimate mentions of legal terminology.
