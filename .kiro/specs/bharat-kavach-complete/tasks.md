# Implementation Plan: Bharat Kavach Complete

## Overview

This plan converts the 12 completion gaps into a sequenced set of coding tasks following the critical path:
backend bug fixes → backend feature additions → new frontend components → Dashboard wiring & layout → test suite setup. Each task builds on its predecessors so there is never hanging or orphaned code.

## Tasks

- [x] 1. Fix backend import and database bugs
  - [x] 1.1 Fix `database.py` SQLAlchemy import error
    - In `backend/database.py`, remove `create_dotenv` from the `from sqlalchemy import ...` line; keep all other symbols (`create_engine`, `Column`, `Integer`, `String`, `Float`, `DateTime`, `Boolean`, `JSON`)
    - Add `city = Column(String, nullable=True)` field to the `CaseReport` ORM class
    - After `Base.metadata.create_all(bind=engine)`, add a startup migration guard that runs `ALTER TABLE case_reports ADD COLUMN city VARCHAR` wrapped in a try/except so it is a no-op when the column already exists (requires importing `text` from `sqlalchemy`)
    - _Requirements: 1.1, 1.2, 1.3, 7.2_

  - [x] 1.2 Fix `main.py` import path for `InterventionService`
    - Change `from ai_engines.intervention import InterventionService` to `from services.intervention import InterventionService`
    - Fix `ConnectionManager.broadcast()` to catch per-connection exceptions: collect dead connections in a local list and remove them after the loop, so a disconnecting client does not abort broadcast to all others
    - Add `from sqlalchemy import text` import to `database.py` for the migration guard
    - _Requirements: 1.2, 5.1_

  - [x] 1.3 Write smoke tests for database import and table creation
    - Create `backend/tests/test_database.py`
    - Test 1: `import database` raises no `ImportError` and no `AttributeError`
    - Test 2: after `Base.metadata.create_all`, both `case_reports` and `forensic_documents` tables exist and are queryable (return empty list on a fresh in-memory DB)
    - _Requirements: 1.1, 1.3_

- [x] 2. Extend `/analyze` endpoint with auto-intervention and full response model
  - [x] 2.1 Add kill-switch logic to `/analyze` in `main.py`
    - Add `city: Optional[str] = None` field to `TranscriptRequest` Pydantic model
    - After computing `risk_score = analysis.confidence * 100` and `stage`, add the conditional kill-switch block: if `risk_score > 85` and `stage == "Financial Demand / UPI Request"`, call `InterventionService.trigger_kill_switch(scam_type="Digital Arrest", victim_id=request.user_id)`; store returned `actions_taken` list in `new_case.interventions`; broadcast `KILL_SWITCH_TRIGGERED` WebSocket message
    - Wrap the kill-switch call in try/except; on exception log it and set `intervention_triggered=False`, `intervention_error=f"Intervention failed: {str(e)}"`, and `new_case.interventions=[]`
    - Store `request.city` in `new_case.city` before `db.commit()`
    - Extend `/analyze` response to include `risk_score`, `stage`, `legal_citations`, `intervention_triggered`, and conditionally `intervention_result` or `intervention_error`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6, 5.7_

  - [x] 2.2 Write property test for kill-switch threshold (Property 6)
    - Create `backend/tests/test_analyze_endpoint.py`
    - **Property 6: Kill-switch fires iff both threshold conditions are met**
    - **Validates: Requirements 5.1, 5.6**
    - Use `hypothesis` `@given(st.floats(0, 1), st.text())`: assert `trigger_kill_switch` is called via mock iff `confidence * 100 > 85 and stage == "Financial Demand / UPI Request"`

  - [x] 2.3 Write example tests for intervention persistence (Property 7)
    - Add to `backend/tests/test_analyze_endpoint.py`
    - **Property 7: Intervention data persists to DB and appears in HTTP response**
    - **Validates: Requirements 5.2, 5.3**
    - Example test: mock `BehavioralClassifier` returning `confidence=0.90` and `stage="Financial Demand / UPI Request"`; mock `InterventionService`; POST to `/analyze` via `TestClient`; assert HTTP 200 response contains `intervention_triggered: true` and non-empty `intervention_result`; read CaseReport from test DB and assert `interventions` is non-empty
    - Example test: same mocks, `confidence=0.90` but `stage="Authority Impersonation"` → assert `intervention_triggered: false` and no `trigger_kill_switch` call
    - Example test: `InterventionService` raises → assert HTTP 200 with `intervention_triggered: false` and `intervention_error` key present
    - _Requirements: 5.2, 5.3, 5.6, 5.7_

- [x] 3. Add `/metrics` endpoint and fix `EvaluationFramework`
  - [x] 3.1 Fix `eval_metrics.py` and promote `TEST_CASES` constant
    - In `backend/tests/eval_metrics.py`, fix the field name bug: replace `beh_analysis.risk_score` with `beh_analysis.confidence * 100` stored in a local `risk_score` variable; update the prediction logic to use this variable
    - Promote the 40-sample list from inside the `if __name__ == "__main__":` block to a module-level constant named `TEST_CASES` (the list already exists — move it above the class or immediately after imports)
    - Add `"mode": None` as a placeholder key returned by `calculate_metrics()` so the endpoint can override it
    - Add `hypothesis` to `backend/requirements.txt`
    - _Requirements: 10.2, 10.3_

  - [x] 3.2 Implement `GET /metrics` endpoint in `main.py`
    - Add `GET /metrics` route: if `MOCK_MODE` return hardcoded JSON with `mode="mock"`, `precision=0.93`, `recall=0.91`, `false_positive_rate=0.04`, `confusion_matrix={"tp":27,"tn":10,"fp":1,"fn":2}`, `total_samples=40`
    - In live mode, import `EvaluationFramework` and `TEST_CASES` from `tests.eval_metrics`, instantiate with `GOOGLE_API_KEY`, call `run_eval(TEST_CASES)` then `calculate_metrics(results)`, set `metrics["mode"]="live"`, return the dict
    - Wrap live-mode block in try/except; on exception raise `HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [x] 3.3 Write tests for `/metrics` endpoint
    - Create `backend/tests/test_metrics.py`
    - Test 1: call `GET /metrics` with `MOCK_MODE=True`; assert HTTP 200, all six required fields present, `mode == "mock"`, `precision >= 0.92`, `recall >= 0.90`, `false_positive_rate <= 0.05`, and `tp + tn + fp + fn == total_samples`
    - Test 2: call `calculate_metrics()` directly with a known confusion matrix `{tp:3, tn:3, fp:1, fn:1}`; assert `precision == 0.75`, `recall == 0.75`, `false_positive_rate == 0.25`
    - _Requirements: 10.3, 10.4_

- [x] 4. Create environment configuration file
  - [x] 4.1 Create `.env.example` and verify `.gitignore`
    - Create `bharat-kavach/.env.example` with a comment block instructing the developer to copy the file to `.env`, followed by a comment explaining `GOOGLE_API_KEY` is required for Gemini 1.5 Flash features, followed by the line `GOOGLE_API_KEY=your_google_api_key_here`
    - Verify `bharat-kavach/.gitignore` contains a line `.env` (it already does per current file) and does NOT contain `.env.example`; no change needed to `.gitignore` since `.env` is already listed
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 5. Checkpoint — backend is stable
  - Ensure all tests pass (`pytest backend/tests/`), ensure the backend starts cleanly with `uvicorn main:app` (or `MOCK_MODE` active), ask the user if questions arise.

- [x] 6. Set up frontend test framework
  - [x] 6.1 Add Vitest and testing libraries to frontend
    - In `frontend/package.json`, add `"test": "vitest --run"` to the `scripts` section
    - Add to `devDependencies` (exact versions): `"vitest": "^1.6.0"`, `"@testing-library/react": "^16.0.0"`, `"@testing-library/user-event": "^14.5.2"`, `"jsdom": "^24.1.0"`, `"fast-check": "^3.19.0"`
    - In `frontend/vite.config.js`, add a `test` block: `{ environment: "jsdom", globals: true }`
    - _Requirements: all frontend testing tasks_

- [x] 7. Create `TranscriptPanel` component
  - [x] 7.1 Implement `TranscriptPanel.jsx`
    - Create `frontend/src/components/dashboard/TranscriptPanel.jsx`
    - Internal state: `transcript` (string), `loading` (boolean), `error` (string|null)
    - Render: a heading "Live Transcript Analysis", a `<textarea>` with `maxLength={10000}` and placeholder "Paste conversation transcript here...", and an "ANALYZE" button
    - On submit: if `transcript.trim()` is empty, set error "Transcript cannot be empty" and return; otherwise set `loading=true`, clear error, create an `AbortController` with a 30-second timeout, POST `{transcript, user_id: "OFFICER_001"}` to `http://localhost:8000/analyze`; on success call `onResult(data)` and clear error; on failure (catch, non-2xx, or abort) set error "Analysis failed. Please try again."; always set `loading=false` in finally
    - While `loading` is true: disable the "ANALYZE" button and show a spinner inside it
    - Props: `onResult(data)` callback
    - _Requirements: 2.1, 2.2, 2.6, 2.7, 2.8, 2.9_

  - [x] 7.2 Write property test for TranscriptPanel (Property 1)
    - Create `frontend/src/components/dashboard/__tests__/TranscriptPanel.test.jsx`
    - **Property 1: Non-empty transcript always triggers a POST**
    - **Validates: Requirements 2.2, 8.2**
    - Use `fc.string({ minLength: 1 })` from `fast-check`; for each generated non-empty string, mock `fetch`, render `TranscriptPanel`, type the string, click ANALYZE, assert `fetch` was called exactly once with the correct endpoint and body
    - Example test: empty/whitespace input → `fetch` not called, error "Transcript cannot be empty" displayed
    - Example test: loading state disables button until response arrives
    - Example test: fetch rejection sets error "Analysis failed. Please try again."

- [x] 8. Create `DocumentPanel` component
  - [x] 8.1 Implement `DocumentPanel.jsx`
    - Create `frontend/src/components/dashboard/DocumentPanel.jsx`
    - Internal state: `file` (File|null), `loading` (boolean), `result` (object|null), `error` (string|null)
    - Render: heading "Document Forensics", a file input accepting `image/jpeg,image/png,application/pdf`, and an "ANALYZE DOCUMENT" button
    - On file selection: validate MIME type; if not `image/jpeg`, `image/png`, or `application/pdf`, set error "Unsupported file type. Please upload a JPEG, PNG, or PDF." and clear the file; if `file.size > 10 * 1024 * 1024` set error "File too large. Maximum 10 MB."
    - On submit: if no file, set error "Please select a document to analyze" and return; set `loading=true`, POST multipart form with `file` field to `http://localhost:8000/analyze-document` using `AbortController` 30s timeout; on success set `result`; on failure set error "Document analysis failed. Please try again."; always `loading=false`
    - Result rendering: display `verdict`, `Math.round(confidence_score * 100) + "%"`, `explanation`; iterate `Object.entries(forensic_signals)` and render each key as a labeled div with a bar whose inline width style is `Math.round(value * 100) + "%"`; if `verdict.includes("Fake") && confidence_score >= 0.75` add red border to result container and display "HIGH FORGERY CONFIDENCE"
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x] 8.2 Write property tests for DocumentPanel (Properties 3 and 4)
    - Create `frontend/src/components/dashboard/__tests__/DocumentPanel.test.jsx`
    - **Property 3: Forgery alert threshold is correctly applied**
    - **Validates: Requirements 3.5**
    - Use `fc.record({ verdict: fc.string(), confidence_score: fc.float({ min: 0, max: 1 }) })` to generate responses; render DocumentPanel with mocked fetch returning each record; assert "HIGH FORGERY CONFIDENCE" shown iff `verdict.includes("Fake") && confidence_score >= 0.75`
    - **Property 4: Document forensic signals render as proportional progress bars**
    - **Validates: Requirements 3.4**
    - Use `fc.dictionary(fc.string(), fc.float({ min: 0, max: 1 }))` to generate `forensic_signals`; assert each key has a rendered bar whose width style equals `Math.round(value * 100) + "%"`

- [x] 9. Create `CurrencyPanel` component
  - [x] 9.1 Implement `CurrencyPanel.jsx`
    - Create `frontend/src/components/dashboard/CurrencyPanel.jsx`
    - Internal state: `file`, `loading`, `result`, `error` (same pattern as DocumentPanel)
    - Render: heading "Currency Verification", file input accepting `image/jpeg,image/png` only, "VERIFY NOTE" button
    - On file selection: validate MIME type; if not `image/jpeg` or `image/png`, set error "Unsupported file type. Please upload a JPEG or PNG image."
    - On submit: if no file, set error "Please select a currency image to verify" and return; set `loading=true` and clear previous `result` to `null` immediately (prevents stale data); POST multipart to `http://localhost:8000/analyze-currency` with 30s timeout; on success set `result`; on failure set error "Currency verification failed. Please try again."; always `loading=false`
    - Result rendering: display `"Note Type: " + result.note_type`; display thread status; if `signals.reason` present display `"Reason: " + signals.reason`; render red badge "SUSPICIOUS NOTE DETECTED" when `signals.is_suspicious` is `true`; render green badge "NOTE APPEARS GENUINE" when `false`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [x] 9.2 Write property test for CurrencyPanel (Property 5)
    - Create `frontend/src/components/dashboard/__tests__/CurrencyPanel.test.jsx`
    - **Property 5: Currency suspicion badge is correctly toggled**
    - **Validates: Requirements 4.4, 4.5**
    - Use `fc.boolean()` to generate `is_suspicious`; mock fetch returning `{ note_type: "500_INR", signals: { thread_detected: true, is_suspicious: generated } }`; assert red badge "SUSPICIOUS NOTE DETECTED" shown when true, green badge "NOTE APPEARS GENUINE" shown when false — mutually exclusive

- [x] 10. Rewrite `FraudNetwork` with live case data
  - [x] 10.1 Implement live-data `FraudNetwork.jsx`
    - Replace the entire static content of `frontend/src/components/forensics/FraudNetwork.jsx`
    - Accept `cases` array as a prop (passed from Dashboard)
    - Implement `deriveNetwork(cases)`: filter cases where `risk_score > 70`; if none return `null`; determine primary suspect as the case with the latest `timestamp` (tiebreak: largest `id`); scan all cases' `transcript` fields for 10-digit phone numbers matching `/[6-9]\d{9}/g`; collect unique numbers in a Set; count contributing case IDs for the badge
    - If `deriveNetwork` returns `null`, render "No high-risk cases detected" instead of SVG
    - If fetch error (propagated via prop or internal fetch error), render "Network data unavailable"
    - Render SVG: Primary Suspect node at (200, 150); phone nodes distributed in a circle at radius 90px with equal `cos/sin` angular spacing; draw edge (Connection) from center to each phone node
    - Replace static badge "CLUSTERING ACTIVE" with `"{linkedCount} CASES LINKED"`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7_

  - [x] 10.2 Write property tests for FraudNetwork (Properties 8 and 9)
    - Create `frontend/src/components/forensics/__tests__/FraudNetwork.test.jsx`
    - **Property 8: FraudNetwork primary suspect selection is deterministic**
    - **Validates: Requirements 6.2, 6.4**
    - Use `fc.array(fc.record({ id: fc.integer(), risk_score: fc.float({ min: 0, max: 100 }), timestamp: fc.date(), transcript: fc.string() }))` to generate case arrays; call `deriveNetwork`; assert selected primary is the case with highest timestamp among risk>70 (id tiebreak); assert null when no case has risk>70
    - **Property 9: Phone number extraction is regex-complete**
    - **Validates: Requirements 6.1, 6.3**
    - Use `fc.array(fc.stringMatching(/[6-9]\d{9}/))` to generate phone arrays; embed them in transcripts; assert all generated numbers are present in extracted set and no false positives appear

- [x] 11. Rewrite `CrimeMap` with India SVG and dynamic hotspots
  - [x] 11.1 Implement India SVG `CrimeMap.jsx`
    - Replace the entire content of `frontend/src/components/forensics/CrimeMap.jsx`
    - Accept `cases` array as a prop (passed from Dashboard) and an optional `fetchError` boolean
    - Embed the India SVG outline as an inline `<svg viewBox="0 0 500 580">` path covering recognizable coastline and major state outlines (no external dependencies)
    - Define `CITY_COORDS` lookup table with SVG coordinates for: Delhi (220,120), Mumbai (130,280), Bangalore (195,390), Chennai (250,410), Kolkata (340,210), Hyderabad (220,330), Pune (145,300), Ahmedabad (110,200)
    - Implement `groupByCity(cases)`: filter cases where `c.city` is a key in `CITY_COORDS`; count cases per city; skip cases with null/undefined/unknown city
    - Implement `pinColor(count)`: return `"#ef4444"` when count ≥ 5, `"#f97316"` when 2–4, `"#eab308"` when 1
    - For each city with cases, render two Framer Motion SVG `<circle>` elements at the city's coordinates: a pulse halo (`animate={{ r: [6, 16, 6], opacity: [0.6, 0, 0.6] }}`, `transition={{ repeat: Infinity, duration: 2 }}`) and a solid pin circle; add a `<text>` label showing city name and case count
    - If `cases` is empty array, render India outline + text "No incidents reported" below map
    - If `fetchError` is true, render India outline + text "Data unavailable" below map
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 11.2 Write property test for CrimeMap pin coloring (Property 10)
    - Create `frontend/src/components/forensics/__tests__/CrimeMap.test.jsx`
    - **Property 10: CrimeMap pin color matches case-count thresholds**
    - **Validates: Requirements 7.4**
    - Use `fc.integer({ min: 1, max: 20 })` to generate case counts per city; for each count assert `pinColor(count)` returns `"#ef4444"` when ≥5, `"#f97316"` when 2–4, `"#eab308"` when 1
    - Example test: empty cases array renders "No incidents reported" text
    - Example test: `fetchError=true` renders "Data unavailable" text

- [x] 12. Rewrite `CitizenApp` with multilingual support and real API calls
  - [x] 12.1 Implement multilingual `CitizenApp.jsx`
    - Replace the entire content of `frontend/src/components/dashboard/CitizenApp.jsx`
    - Add `TRANSLATIONS` map at module level with keys `en`, `hi`, `ta`; each language object must contain exactly: `alertTitle`, `stagePrefix`, `reportBtn`, `helplineBtn`, `safeMessage`, `offlineFallback`, `unknownStage` — all as non-empty strings (use the values from the design document)
    - Add `language` state defaulting to `"en"`; render three language-selector buttons (EN / हिन्दी / தமிழ்) at the top of the component; active language button has a distinct active style
    - Add `loading` state and `alertState` state (null | { score, stage } | { offline: true })
    - Rewrite `sendMessage()`: if input is empty return; add user message to messages; clear input; set `loading=true`, `alertState=null`; create `AbortController` with 10s timeout; POST `{ transcript: input }` to `http://localhost:8000/analyze`; on success parse `risk_score = data.risk_score ?? (data.confidence * 100)` and set `alertState({ score, stage: data.stage })`; on catch set `alertState({ offline: true })`; always set `loading=false`
    - While `loading` is true, append a typing-indicator message `{ id: "typing", sender: "typing" }` to the rendered message list (do not mutate the messages state array); render it as three animated dots using Framer Motion `staggerChildren`
    - Conditionally render alert banner below messages: if `alertState?.offline` → offline fallback text from selected language; if `alertState?.score >= 60` → red alert with `TRANSLATIONS[language].alertTitle`, stage label (use `alertState.stage ?? TRANSLATIONS[language].unknownStage`), REPORT button, CALL 1930 button — all labeled from the translation map; if `alertState?.score < 60` → green safe-message text from translation map
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 12.2 Write property tests for CitizenApp (Properties 11 and 13)
    - Create `frontend/src/components/dashboard/__tests__/CitizenApp.test.jsx`
    - **Property 11: CitizenApp alert language is always consistent with selected language**
    - **Validates: Requirements 8.3, 8.5, 8.7**
    - Use `fc.constantFrom("en", "hi", "ta")` and `fc.float({ min: 60, max: 100 })` for language and score; mock fetch; render CitizenApp, select language, submit message; assert all visible alert strings come exclusively from `TRANSLATIONS[language]`
    - **Property 13: Translation map completeness**
    - **Validates: Requirements 8.7**
    - Static assertion: for each of `["en", "hi", "ta"]`, assert all seven keys are present and are non-empty strings
    - Example test: score < 60 renders safe message, not alert banner
    - Example test: offline fallback shown when fetch rejects or times out

- [x] 13. Wire Dashboard: layout, state, WebSocket, and export
  - [x] 13.1 Update `Dashboard.jsx` state, WebSocket handler, and grid layout
    - In `frontend/src/components/dashboard/Dashboard.jsx`:
    - Add `id`, `transcript`, and `caseHistory` (rename from `history` for clarity) to initial `caseData` state; keep `score`, `stage`, `signals`, `findings`, `interventions`
    - Add `toast` state (string|null) for export notifications
    - In the `useEffect` WebSocket `onmessage` handler: handle `FORENSIC_UPDATE` by updating `caseData.id`, `.score`, `.stage`, `.findings`, and all four `.signals` fields using the `hasFalseFindings` helper; handle `KILL_SWITCH_TRIGGERED` by appending a new intervention entry (with `type`, `action`, `details`, `timestamp`, `incident_id`, `actions_taken`) to `caseData.interventions`
    - Re-fetch `/cases` on `FORENSIC_UPDATE` to refresh `caseData.history` (which feeds FraudNetwork and CrimeMap)
    - Add `handleExport()` function: if `caseData.score === 0`, set toast and return; otherwise build the intelligence package object with the seven required fields, conditionally add `intervention_result` if an intervention with `incident_id` exists, create a Blob, trigger `<a>` download with filename pattern `bharat-kavach-case-{id}-{yyyyMMddTHHmmss}.json`, revoke object URL
    - Add `hasFalseFindings` helper: returns `true` if any finding has `verdict === "confirmed_false"`
    - Wire `EXPORT INTELLIGENCE PACKAGE` button to `handleExport`
    - Fix import of `Map` icon: the current code uses `Map` variable from `lucide-react` re-aliased as `MapIcon` in the import but uses `Map` in JSX — use `MapIcon` consistently throughout JSX
    - _Requirements: 2.3, 2.4, 2.5, 5.4, 5.5, 6.5, 7.7, 9.1, 9.2, 9.3, 9.4, 9.5, 12.2_

  - [x] 13.2 Add new panels and `ForensicSignals` to Dashboard grid
    - Import `TranscriptPanel`, `DocumentPanel`, `CurrencyPanel` from their new files
    - In the `col-span-3` left column: insert `<ForensicSignals signals={caseData.signals} />` between `<RiskMeter>` and `<CaseHistory>` — the import already exists but is not rendered
    - In the `col-span-5` center column: add `<TranscriptPanel onResult={(data) => { setCaseData(prev => ({ ...prev, transcript: prev.transcript })) }} />` at the top; add `<DocumentPanel />` and `<CurrencyPanel />` below `<FraudNetwork>`
    - Pass `cases={caseData.history}` prop to `<FraudNetwork>` and `<CrimeMap>`
    - Wire `TranscriptPanel`'s `onResult` to store the submitted transcript in `caseData.transcript` (the transcript text must be captured in Dashboard state before the POST so the export package has access to it; pass `onSubmit` callback to `TranscriptPanel` that receives the raw transcript string before sending)
    - Render toast notification: when `toast` is non-null, render a fixed bottom-center div that auto-dismisses after 3 seconds via `setTimeout(() => setToast(null), 3000)`
    - _Requirements: 2.1, 3.1, 4.1, 12.1, 12.5_

  - [x] 13.3 Write property and example tests for Dashboard export and signals (Properties 2, 7, 12, 14)
    - Create `frontend/src/components/dashboard/__tests__/Dashboard.test.jsx`
    - **Property 2: FORENSIC_UPDATE message drives all Dashboard state fields**
    - **Validates: Requirements 2.3, 2.4, 2.5, 12.2**
    - Use `fc.record({ score: fc.float({min:0,max:100}), stage: fc.string(), findings: fc.array(...), id: fc.integer() })` to generate FORENSIC_UPDATE payloads; simulate WS message; assert all six state fields (`score`, `stage`, `findings`, `id`, and all four `signals.*`) updated correctly per mapping rules
    - **Property 12: Intelligence package export contains exactly the required fields**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.5**
    - Use `fc.record` to generate `caseData` with `score > 0`; call `handleExport`; intercept blob content; parse JSON; assert exactly 7 keys present (plus conditional `intervention_result`)
    - **Property 14: ForensicSignals Alert state tracks thresholds**
    - **Validates: Requirements 12.3, 12.4**
    - Use `fc.float({min:0,max:100})` for `behavioral` and `legal`; render `ForensicSignals`; assert "Behavioral Arc" bar has `status="Alert"` iff `behavioral > 60`; assert "Legal Grounding" bar has `status="Alert"` iff `legal < 50`
    - Example test: `caseData.score === 0` on export → toast "No active case to export. Analyze a transcript first." shown, no download triggered

- [ ] 14. Final checkpoint — full system integration verified
  - Ensure `npm run test` passes all frontend tests (run from `frontend/` with `vitest --run`)
  - Ensure `pytest backend/tests/` passes all backend tests
  - Ensure backend starts without errors in MOCK_MODE (`GOOGLE_API_KEY` unset)
  - Ask the user if questions arise before proceeding to demo preparation.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP path; all core functionality is covered by the unmarked tasks
- Tasks 1.1 and 1.2 must complete before any other backend or frontend task is run against a live server
- Tasks 6.1 (Vitest setup) must complete before any frontend test tasks (7.2, 8.2, 9.2, 10.2, 11.2, 12.2, 13.3)
- FraudNetwork (task 10) and CrimeMap (task 11) both depend on the `cases` prop wired in Dashboard (task 13.2) — the components are self-contained but will display empty states until the prop is connected
- The `city` column added in task 1.1 has no UI for population yet; the CrimeMap gracefully skips records with `null` city. To demo hotspots, seed test cases via the `/analyze` endpoint with a `city` field in the request body (added in task 2.1)
- Each property test is tagged in a comment: `// Feature: bharat-kavach-complete, Property N: <title>`
- All property tests run minimum 100 iterations by default (fast-check/hypothesis defaults)
- The `ForensicSignals` component is already correctly implemented and imported in `Dashboard.jsx`; task 13.2 is a single JSX insertion
- The `LegalAudit` component references `finding.claim` but the backend serializes the field as `claim_extracted` — ensure the LegalAudit rendering uses the correct field name from the actual `/analyze` response shape; verify against the `LegalClaim` Pydantic model in `legal_rag.py` during task 13.1

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "2.1", "3.1", "4.1", "6.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "7.1", "8.1", "9.1", "10.1", "11.1", "12.1"] },
    { "id": 3, "tasks": ["3.3", "7.2", "8.2", "9.2", "10.2", "11.2", "12.2", "13.1"] },
    { "id": 4, "tasks": ["13.2"] },
    { "id": 5, "tasks": ["13.3"] }
  ]
}
```
