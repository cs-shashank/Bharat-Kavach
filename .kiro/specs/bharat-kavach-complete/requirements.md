# Requirements Document

## Introduction

Bharat Kavach is an AI-powered Digital Public Safety Intelligence platform built for hackathon Problem 6 ("AI for Digital Safety: Defeating Counterfeiting, Fraud & Digital Arrest Scams"). The platform is partially built with a FastAPI backend (Gemini AI, OpenCV, SQLite) and a React/Vite/TailwindCSS v4 frontend. This document captures requirements for completing the 12 identified gaps — spanning backend bug fixes, new UI panels, automatic intervention logic, live data wiring, geospatial visualization, multilingual citizen protection, exportable reports, evaluation metrics, and environment configuration — to reach a winning hackathon submission.

Judging criteria: Innovation (25%), Business Impact (25%), Technical Excellence (20%), Scalability (15%), User Experience (15%). Evaluation focus: scam detection precision/recall, counterfeit detection accuracy, fraud network detection lead time, false positive rate, auditability of automated actions.

---

## Glossary

- **BehavioralClassifier**: The AI engine (`backend/ai_engines/behavioral.py`) that uses Gemini 1.5 Flash to classify conversation transcripts into scam escalation stages.
- **ProtocolVerifier**: The engine (`backend/ai_engines/protocol.py`) that flags critical legal protocol violations (e.g., arrest via video call).
- **LegalRAG**: The engine (`backend/ai_engines/legal_rag.py`) that cross-references transcripts against BNS 2024 legal knowledge base.
- **VisionForensics**: The engine (`backend/ai_engines/vision.py`) that analyzes uploaded document images for forgery signals using OpenCV and Gemini.
- **CurrencyVerifier**: The engine (`backend/ai_engines/currency.py`) that analyzes uploaded currency note images for counterfeit signals using OpenCV.
- **InterventionService**: The service (`backend/services/intervention.py`) that simulates kill-switch actions (UPI_HOLD, TELECOM_FLAG, POLICE_ALERT).
- **Dashboard**: The officer-facing React UI (`frontend/src/components/dashboard/Dashboard.jsx`) showing the real-time forensic investigation interface.
- **FraudNetwork**: The React component (`frontend/src/components/forensics/FraudNetwork.jsx`) visualizing linked suspect phone numbers and accounts as a graph.
- **CrimeMap**: The React component (`frontend/src/components/forensics/CrimeMap.jsx`) visualizing geospatial distribution of cases on a map.
- **CitizenApp**: The React component (`frontend/src/components/dashboard/CitizenApp.jsx`) simulating a WhatsApp-like citizen-facing scam detector.
- **ForensicSignals**: The React component (`frontend/src/components/forensics/ForensicSignals.jsx`) displaying four behavioral/legal/vision/protocol signal bars.
- **Risk_Score**: A float 0–100 representing the probability that a transcript represents a scam; computed as `analysis.confidence * 100` by the `/analyze` endpoint.
- **Stage**: A string label for the current scam escalation phase, one of: Normal Conversation, Authority Impersonation, Digital Confinement / Isolation, Fabricated Evidence, Urgency / Fear Injection, Financial Demand / UPI Request.
- **Kill_Switch**: The automated intervention triggered by InterventionService when risk conditions are met; simulates UPI_HOLD + TELECOM_FLAG + POLICE_ALERT.
- **Intelligence_Package**: A structured export (JSON) containing case metadata, transcript, risk score, legal findings, intervention log, and timestamp.
- **WebSocket**: The persistent bidirectional connection at `ws://localhost:8000/ws/{client_id}` used for real-time broadcast of forensic updates to the Dashboard.
- **MOCK_MODE**: The backend fallback mode active when `GOOGLE_API_KEY` is absent; returns hardcoded demo responses.
- **EvaluationFramework**: The class in `backend/tests/eval_metrics.py` that runs the 40-sample test set and computes precision, recall, and false positive rate.
- **Hotspot**: A geographic cluster of case reports rendered as an animated pin on the CrimeMap.

---

## Requirements

### Requirement 1: Database Import Bug Fix

**User Story:** As a developer running the backend server, I want `database.py` to import only valid SQLAlchemy symbols, so that the server starts without an `ImportError`.

#### Acceptance Criteria

1. THE `database.py` module SHALL import `create_engine` from `sqlalchemy` and SHALL NOT import `create_dotenv` from `sqlalchemy`.
2. WHEN the FastAPI server is started with `uvicorn main:app`, THE Backend SHALL start successfully — emitting the "Application startup complete" log line to stdout — within 30 seconds, without any `ImportError` or `AttributeError` related to SQLAlchemy imports.
3. WHEN `Base.metadata.create_all(bind=engine)` is called on startup, THE Backend SHALL create the `case_reports` and `forensic_documents` tables in `bharat_kavach.db` without raising any exception, AND both tables SHALL be present and queryable (returning an empty result set) immediately after startup completes.

---

### Requirement 2: Live Transcript Analysis Panel

**User Story:** As a law enforcement officer, I want a panel in the Dashboard where I can paste or type a conversation transcript and click "Analyze", so that risk score, scam stage, legal findings, and intervention status update on the Dashboard in real time.

#### Acceptance Criteria

1. THE Dashboard SHALL render a "Live Transcript Analysis" panel containing a multi-line text area (maximum 10,000 characters) and an "ANALYZE" submit button.
2. WHEN the officer submits a non-empty transcript (up to 10,000 characters), THE Dashboard SHALL send a POST request to the `/analyze` endpoint with a JSON body containing a `transcript` field matching the `TranscriptRequest` Pydantic model.
3. WHEN the Backend broadcasts a `FORENSIC_UPDATE` WebSocket message after analysis, THE Dashboard SHALL update the RiskMeter `score` prop with `message.data.score` and the `stage` prop with `message.data.stage` without requiring a page reload.
4. WHEN the Backend broadcasts a `FORENSIC_UPDATE` WebSocket message after analysis, THE Dashboard SHALL update the LegalAudit `findings` prop with `message.data.findings`.
5. WHEN the Backend broadcasts a `FORENSIC_UPDATE` WebSocket message, THE Dashboard SHALL update its state so that all connected officer nodes reflect the new data via the existing WebSocket connection.
6. IF the transcript input is empty when the officer clicks "ANALYZE", THEN THE Panel SHALL display a validation message "Transcript cannot be empty" and SHALL NOT submit the POST request.
7. WHILE the POST request to `/analyze` is in progress (after submission and before the WebSocket `FORENSIC_UPDATE` message is received or an error occurs), THE Panel SHALL display a loading indicator and SHALL disable the "ANALYZE" button to prevent duplicate submissions.
8. WHEN the loading state is active and either a `FORENSIC_UPDATE` WebSocket message is received or the POST request returns an error, THE Panel SHALL remove the loading indicator and re-enable the "ANALYZE" button.
9. IF the POST request to `/analyze` fails (network error or HTTP status ≥ 400) or does not receive a response within 30 seconds, THEN THE Panel SHALL display an error message "Analysis failed. Please try again." and SHALL re-enable the "ANALYZE" button.

---

### Requirement 3: Document Upload and Forensic Analysis Panel

**User Story:** As a law enforcement officer, I want to upload an image of a suspected fake warrant or official document and see VisionForensics results in the Dashboard, so that I can quickly assess document authenticity.

#### Acceptance Criteria

1. THE Dashboard SHALL render a "Document Forensics" panel containing a file upload input that accepts image files (JPEG, PNG) and PDF files up to 10 MB in size, and an "ANALYZE DOCUMENT" button.
2. WHEN the officer uploads a supported file and clicks "ANALYZE DOCUMENT", THE Panel SHALL send a multipart POST request to `/analyze-document` with the file attached as the `file` form field.
3. WHEN the `/analyze-document` endpoint returns a response, THE Panel SHALL display the `verdict` string, `confidence_score` rendered as a whole-number percentage (e.g., 0.88 → "88%"), and `explanation` string from the response.
4. WHEN the `/analyze-document` endpoint returns a response containing a `forensic_signals` object, THE Panel SHALL display each signal key as a labeled progress bar where the bar fill width corresponds to the signal value mapped from its 0.0–1.0 float range to 0%–100% display width.
5. IF the `/analyze-document` endpoint returns a response where `verdict` contains the substring "Fake" and `confidence_score` is ≥ 0.75, THEN THE Panel SHALL highlight the result area with a red alert border and display the text "HIGH FORGERY CONFIDENCE" within that same result area.
6. WHILE a document upload and analysis request is in progress, THE Panel SHALL display a loading spinner and SHALL disable the "ANALYZE DOCUMENT" button.
7. IF no file is selected when the officer clicks "ANALYZE DOCUMENT", THEN THE Panel SHALL display the message "Please select a document to analyze" and SHALL NOT submit the request.
8. IF the officer attempts to upload a file whose MIME type is not `image/jpeg`, `image/png`, or `application/pdf`, THEN THE Panel SHALL display the message "Unsupported file type. Please upload a JPEG, PNG, or PDF." and SHALL NOT submit the request.
9. IF the `/analyze-document` request fails (network error, HTTP status ≥ 400, or no response within 30 seconds), THEN THE Panel SHALL display the message "Document analysis failed. Please try again." and SHALL re-enable the "ANALYZE DOCUMENT" button.

---

### Requirement 4: Currency Image Upload and Verification Panel

**User Story:** As a law enforcement officer, I want to upload an image of a suspect currency note and see CurrencyVerifier results in the Dashboard, so that I can identify potential counterfeit notes at the scene.

#### Acceptance Criteria

1. THE Dashboard SHALL render a "Currency Verification" panel containing a file upload input that accepts JPEG and PNG image files up to 10 MB in size, and a "VERIFY NOTE" button.
2. WHEN the officer uploads a supported image file and clicks "VERIFY NOTE", THE Panel SHALL send a multipart POST request to `/analyze-currency` with the file attached as the `file` form field.
3. WHEN the `/analyze-currency` endpoint returns a response, THE Panel SHALL display the `note_type` field as "Note Type: {value}", the `signals.thread_detected` boolean as "Security Thread: Detected" or "Security Thread: Not Detected", and the `signals.is_suspicious` boolean as its human-readable verdict label per criteria 4 and 5. WHEN the response `signals` object contains a `reason` field, THE Panel SHALL also display it as "Reason: {value}".
4. IF the response `signals.is_suspicious` is `true`, THEN THE Panel SHALL render a red badge with the text "SUSPICIOUS NOTE DETECTED".
5. IF the response `signals.is_suspicious` is `false`, THEN THE Panel SHALL render a green badge with the text "NOTE APPEARS GENUINE".
6. WHILE a currency verification request is in progress, THE Panel SHALL display a loading spinner, SHALL disable the "VERIFY NOTE" button, and SHALL clear any result from a prior verification to prevent stale data display.
7. IF no file is selected when the officer clicks "VERIFY NOTE", THEN THE Panel SHALL display "Please select a currency image to verify" and SHALL NOT submit the request.
8. IF the officer attempts to upload a file whose MIME type is not `image/jpeg` or `image/png`, THEN THE Panel SHALL display "Unsupported file type. Please upload a JPEG or PNG image." and SHALL NOT submit the request.
9. IF the `/analyze-currency` request fails (network error, HTTP status ≥ 400, or no response within 30 seconds), THEN THE Panel SHALL display "Currency verification failed. Please try again." and SHALL re-enable the "VERIFY NOTE" button.

---

### Requirement 5: Automatic Intervention Trigger on High-Risk Analysis

**User Story:** As a platform operator, I want the `/analyze` endpoint to automatically trigger the InterventionService kill-switch when a transcript is classified as high-risk, so that protective actions are initiated before financial loss occurs.

#### Acceptance Criteria

1. WHEN the `/analyze` endpoint processes a transcript and the computed `risk_score` is strictly greater than 85 AND the `stage` equals "Financial Demand / UPI Request", THE Backend SHALL call `InterventionService.trigger_kill_switch(scam_type="Digital Arrest", victim_id=request.user_id)`.
2. WHEN `InterventionService.trigger_kill_switch()` is called and returns successfully, THE Backend SHALL persist the intervention result by storing the returned `actions_taken` list and `incident_id` in the `interventions` JSON field of the saved `CaseReport` database record before committing the transaction.
3. WHEN an intervention is triggered successfully, THE Backend SHALL include `intervention_triggered: true` and an `intervention_result` object (containing `actions_taken`, `incident_id`) in the `/analyze` HTTP response body.
4. WHEN an intervention is triggered, THE Backend SHALL broadcast a `KILL_SWITCH_TRIGGERED` WebSocket message containing `actions_taken`, `incident_id`, `risk_score`, `stage`, and a UTC ISO 8601 `timestamp` to all connected Dashboard clients.
5. WHEN the Dashboard receives a `KILL_SWITCH_TRIGGERED` WebSocket message, THE Dashboard SHALL append a new entry to the InterventionLog with `type: "FINANCIAL"`, `action` set to the first item of `actions_taken`, `details` containing the `incident_id`, and `timestamp` from the message payload.
6. IF the `risk_score` is strictly greater than 85 but the `stage` is NOT "Financial Demand / UPI Request", THEN THE Backend SHALL NOT call `InterventionService.trigger_kill_switch()`, SHALL set `intervention_triggered: false` in the response, AND SHALL omit the `intervention_result` field from the response entirely.
7. IF `InterventionService.trigger_kill_switch()` raises an exception during a qualifying high-risk analysis, THEN THE Backend SHALL log the exception, SHALL set `intervention_triggered: false` and include an `intervention_error: "Intervention failed: {exception message}"` field in the response, and SHALL still save the `CaseReport` to the database with an empty `interventions` list.

---

### Requirement 6: Fraud Network Wired to Real Case Data

**User Story:** As an investigator, I want the FraudNetwork graph to display actual phone numbers, account identifiers, and linkages extracted from real case records, so that I can visually trace the fraud syndicate from live data.

#### Acceptance Criteria

1. WHEN the Dashboard mounts, THE FraudNetwork component SHALL fetch case records from the `/cases` endpoint and extract network nodes by: (a) using each case's `user_id` as a potential node identifier, and (b) scanning each case's `transcript` field for 10-digit phone numbers matching the regex `[6-9]\d{9}` and treating each unique match as a Smartphone node.
2. THE FraudNetwork component SHALL render a "Primary Suspect" node using the `user_id` of the case with the highest `timestamp` value among all cases where `risk_score > 70`. IF multiple cases share the same highest timestamp, THE component SHALL use the one with the largest `id` value as the tiebreaker.
3. WHEN cases contain phone number matches per criterion 1(b), THE FraudNetwork component SHALL render each unique phone number as a Smartphone node connected by an edge to the Primary Suspect node.
4. WHEN no cases with `risk_score > 70` exist in the fetched data, THE FraudNetwork component SHALL display the text "No high-risk cases detected" in place of the graph SVG.
5. WHEN the Dashboard receives a `FORENSIC_UPDATE` WebSocket message, THE FraudNetwork component SHALL trigger a full re-fetch of the `/cases` endpoint and re-derive all nodes from the updated case list, replacing all previously rendered nodes and edges.
6. THE FraudNetwork header badge SHALL display "N CASES LINKED" where N is the count of cases that contributed at least one node (Primary Suspect or Smartphone) to the currently rendered graph.
7. IF the `/cases` fetch fails (network error or non-200 response), THE FraudNetwork component SHALL display "Network data unavailable" in place of the graph and SHALL NOT render the static hardcoded placeholder nodes.

---

### Requirement 7: Geospatial Crime Map with India SVG and Dynamic Hotspots

**User Story:** As a law enforcement officer, I want the CrimeMap to display an outline map of India with animated hotspot pins positioned by region, so that I can immediately identify geographic concentration of scam activity.

#### Acceptance Criteria

1. THE CrimeMap component SHALL render an SVG outline of India as its base map, with recognizable external coastline and internal state boundaries, replacing the current rectangular grid placeholder.
2. WHEN the CrimeMap component mounts, THE CrimeMap component SHALL fetch case data from the `/cases` endpoint, extract the `city` field from each case record, and group cases by city name using a lookup table that maps each of the following cities — Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Ahmedabad — to a fixed SVG coordinate within the India outline; cases whose `city` field does not match any entry in the lookup table SHALL be ignored for pin rendering.
3. WHEN a region has one or more cases, THE CrimeMap component SHALL render a pulsing pin at the corresponding SVG coordinate, where the pulse animation completes one full expand-and-fade cycle within 2 seconds and repeats continuously, and the pin is accompanied by a label showing the city name and the total case count for that region.
4. WHEN a region has 5 or more cases, THE CrimeMap SHALL color the pin red (Critical). WHEN a region has 2–4 cases, THE CrimeMap SHALL color the pin orange (High). WHEN a region has exactly 1 case, THE CrimeMap SHALL color the pin yellow (Medium).
5. IF the `/cases` endpoint returns an empty array, THEN THE CrimeMap SHALL render the India SVG outline with no pins and display the text "No incidents reported" below the map. IF the `/cases` endpoint returns a network error or a non-200 response, THEN THE CrimeMap SHALL render the India SVG outline with no pins and display the text "Data unavailable" below the map.
6. IF the `/cases` endpoint is unreachable at mount time, THEN THE CrimeMap SHALL complete the fetch attempt within 10 seconds and, upon timeout, display the "Data unavailable" state as defined in criterion 5.
7. WHEN the Dashboard receives a `FORENSIC_UPDATE` WebSocket message and passes updated `cases` prop to the CrimeMap component, THE CrimeMap SHALL re-render all hotspot pins using the updated `cases` array, replacing any previously rendered pins with pins derived solely from the new prop value.

---

### Requirement 8: Citizen Fraud Shield — Multilingual Real Analysis

**User Story:** As a citizen who suspects they are being scammed, I want to type a message in Hindi, English, or Tamil in the CitizenApp and receive a real Bharat Kavach alert based on AI analysis, so that I can identify and report digital arrest scams in my preferred language.

#### Acceptance Criteria

1. THE CitizenApp SHALL render a language selector allowing the user to choose between English, Hindi (हिन्दी), and Tamil (தமிழ்), defaulting to English on initial render.
2. WHEN the citizen sends a non-empty message, THE CitizenApp SHALL POST the message text to the `/analyze` endpoint as a JSON body with a `transcript` field. IF the message is empty, THE CitizenApp SHALL NOT submit the request.
3. WHEN the `/analyze` endpoint returns (via HTTP response or WebSocket broadcast) a result with `risk_score >= 60`, THE CitizenApp SHALL display a Bharat Kavach alert banner in the selected language warning the citizen of a detected scam pattern.
4. WHEN the `/analyze` endpoint returns a result with `risk_score < 60`, THE CitizenApp SHALL display the safe-message confirmation string for the selected language.
5. THE CitizenApp alert banner for `risk_score >= 60` SHALL display: the scam `stage` label translated into the selected language; a "REPORT" button labeled in the selected language; and a "CALL 1930" button labeled in the selected language. IF the `stage` value is null or unknown, THE CitizenApp SHALL display a generic "Scam detected" stage label in the selected language.
6. WHILE the CitizenApp analysis request is in progress, THE CitizenApp SHALL display a typing indicator animation in the chat area.
7. THE CitizenApp SHALL define static translation maps for all three languages containing at minimum: alert title, scam stage prefix label, report button label, helpline button label, and safe message confirmation text.
8. IF the POST request to `/analyze` fails with a network error or does not respond within 10 seconds, THEN THE CitizenApp SHALL display an offline fallback alert in the selected language advising the user that the message could not be analyzed and to call 1930.

---

### Requirement 9: Intelligence Package Export

**User Story:** As an investigating officer, I want to click "EXPORT INTELLIGENCE PACKAGE" in the Dashboard and download a structured report, so that I can submit auditable case evidence to the cyber crime portal.

#### Acceptance Criteria

1. WHEN the officer clicks "EXPORT INTELLIGENCE PACKAGE" and `caseData.score > 0`, THE Dashboard SHALL compile a report object from the current `caseData` state containing: `case_id`, `transcript`, `risk_score`, `stage`, `legal_findings` (from `legal_citations`), `interventions`, and `exported_at` as an ISO 8601 UTC timestamp string.
2. THE Dashboard SHALL trigger a browser file download of the compiled report as a JSON file. The filename SHALL follow the pattern `bharat-kavach-case-{case_id}-{yyyyMMddTHHmmss}.json` where the timestamp uses the same moment as `exported_at`.
3. THE exported file content SHALL be valid JSON — parseable by `JSON.parse()` without error — and SHALL contain exactly the seven top-level fields: `case_id`, `transcript`, `risk_score`, `stage`, `legal_findings`, `interventions`, `exported_at`.
4. IF `caseData.score === 0` when the officer clicks "EXPORT INTELLIGENCE PACKAGE", THEN THE Dashboard SHALL display a toast notification with the text "No active case to export. Analyze a transcript first." and SHALL NOT trigger any file download.
5. IF the current case triggered an automatic intervention (i.e., `caseData.interventions` contains an entry with an `incident_id` field), THEN THE exported package SHALL include a top-level `intervention_result` object containing `actions_taken`, `incident_id`, and `triggered_at` (the ISO 8601 UTC timestamp of the intervention). IF no automatic intervention was triggered, THE exported package SHALL omit the `intervention_result` field entirely.

---

### Requirement 10: Evaluation Metrics API Endpoint

**User Story:** As a hackathon judge or platform operator, I want a `/metrics` endpoint that returns precision, recall, and false positive rate computed on a hardcoded test set, so that I can verify the platform's detection accuracy during the demo.

#### Acceptance Criteria

1. THE Backend SHALL expose a `GET /metrics` endpoint accessible without authentication that returns an HTTP 200 response within 60 seconds under normal operating conditions.
2. WHEN `GET /metrics` is called in live mode (Gemini active), THE Backend SHALL instantiate `EvaluationFramework` from `backend/tests/eval_metrics.py`, run it against the 40-sample hardcoded test set, and return the computed results.
3. THE `/metrics` response body SHALL be a JSON object containing exactly these fields: `total_samples` (integer), `precision` (float, 0.0–1.0), `recall` (float, 0.0–1.0), `false_positive_rate` (float, 0.0–1.0), `confusion_matrix` (object with integer fields `tp`, `tn`, `fp`, `fn`), and `mode` (string, either `"live"` or `"mock"`).
4. WHEN `GOOGLE_API_KEY` is absent and the backend is in `MOCK_MODE`, THE `/metrics` endpoint SHALL return a hardcoded response with `mode: "mock"`, `precision >= 0.92`, `recall >= 0.90`, `false_positive_rate <= 0.05`, and a `confusion_matrix` whose `tp + tn + fp + fn` equals `total_samples`.
5. THE `/metrics` response SHALL set `mode: "live"` when Gemini is active and `mode: "mock"` when in MOCK_MODE.
6. WHEN `GET /metrics` is called in live mode and `EvaluationFramework` raises any exception, THE Backend SHALL return HTTP 500 with a JSON body containing a `detail` field describing the exception type and message.

---

### Requirement 11: Environment Configuration File

**User Story:** As a developer setting up Bharat Kavach for the first time, I want a `.env.example` file in the project root that documents all required environment variables, so that I can configure the platform without reading the source code.

#### Acceptance Criteria

1. THE file `bharat-kavach/.env.example` SHALL exist and be committed to version control.
2. THE `.env.example` file SHALL contain a line in the format `GOOGLE_API_KEY=your_google_api_key_here` and a comment on the preceding line explaining that this key is required for Gemini 1.5 Flash AI features.
3. THE `.env.example` file SHALL begin with a comment block (lines starting with `#`) that instructs the developer to copy the file to `.env` and populate the values before running the backend server.
4. THE `bharat-kavach/.gitignore` file SHALL contain a line matching `.env` (excluding the populated secrets file from version control).
5. THE `bharat-kavach/.gitignore` file SHALL NOT contain a line matching `.env.example`, so that the example file remains tracked by version control.

---

### Requirement 12: ForensicSignals Integrated into Dashboard Layout

**User Story:** As a law enforcement officer, I want the ForensicSignals component to be visible in the Dashboard alongside the other forensic panels, so that I can monitor behavioral, legal, vision, and protocol signal streams at a glance.

#### Acceptance Criteria

1. THE Dashboard SHALL import and render the `ForensicSignals` component in the main grid layout, passing `caseData.signals` as the `signals` prop.
2. WHEN the Dashboard receives a `FORENSIC_UPDATE` WebSocket message, THE Dashboard SHALL update `caseData.signals` as follows: `behavioral` SHALL be set to `message.data.score`; `legal` SHALL be set to `100` if `message.data.findings` is empty or contains no entries with `verdict === "confirmed_false"`, and `0` if any confirmed-false finding is present; `vision` SHALL be set to `100` (default, until a document analysis result overrides it); `protocol` SHALL be set to `100` (default, until a protocol violation is detected).
3. WHEN `caseData.signals.behavioral` exceeds 60, THE ForensicSignals component SHALL render the "Behavioral Arc" bar with `status="Alert"` (red styling as defined in the existing `SignalIndicator` component). WHILE the `behavioral` value in state remains above 60 within the same browser session, THE component SHALL maintain the Alert state.
4. WHEN `caseData.signals.legal` is less than 50, THE ForensicSignals component SHALL render the "Legal Grounding" bar with `status="Alert"` (red styling).
5. THE ForensicSignals component SHALL be placed within the Dashboard's existing 12-column grid such that on a 1280px-wide viewport it occupies a grid column that renders without horizontal scrolling, sharing or replacing column space within the current `col-span-4` right column (LegalAudit + InterventionLog column).
