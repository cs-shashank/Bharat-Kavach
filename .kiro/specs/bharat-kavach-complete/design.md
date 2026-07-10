# Design Document — Bharat Kavach Complete

## Overview

Bharat Kavach is an AI-powered Digital Public Safety Intelligence platform targeting Indian "Digital Arrest" scams, counterfeit currency, and document forgery. The system pairs a FastAPI/Python backend (Gemini 1.5 Flash, OpenCV, SQLite) with a React 19/Vite/TailwindCSS v4 frontend dashboard.

This design document covers the 12 completion gaps needed to reach a winning hackathon state:

1. Fix the `database.py` import bug (`create_dotenv` → removed)
2. Live Transcript Analysis Panel (new Dashboard section)
3. Document Forensics Upload Panel (new Dashboard section)
4. Currency Verification Upload Panel (new Dashboard section)
5. Automatic kill-switch trigger in `/analyze`
6. FraudNetwork wired to real `/cases` data
7. CrimeMap with India SVG outline and city hotspots
8. CitizenApp multilingual (EN/HI/TA) with real `/analyze` calls
9. Intelligence Package Export (JSON download)
10. `/metrics` endpoint + `EvaluationFramework` implementation
11. `.env.example` environment configuration file
12. `ForensicSignals` integrated into Dashboard layout

### Key Research Findings

- **TailwindCSS v4** uses `@tailwindcss/vite` (plugin-based, no separate config file) — confirmed by `vite.config.js` and `package.json`.
- **Framer Motion v12** is installed; `AnimatePresence` and `motion` APIs are stable.
- The `EvaluationFramework` class in `eval_metrics.py` references `beh_analysis.risk_score` but `AnalysisResult` exposes `confidence` (not `risk_score`). The field name must be corrected during implementation.
- `main.py` imports `InterventionService` from `ai_engines.intervention` (wrong path) — it lives in `services/intervention.py`. This import path bug must be fixed alongside Req 5.
- The existing `Dashboard.jsx` already imports `ForensicSignals` but never renders it in JSX — confirming Req 12 is a one-line addition.
- India SVG outline coordinates are standardized around a 500×580 viewBox for good state-boundary fidelity at dashboard width.

---

## Architecture

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Officer)                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Dashboard.jsx                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │ TranscriptPanel│  │DocumentPanel │  │ CurrencyPanel    │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │   │
│  │         │                  │                    │             │   │
│  │  ┌──────▼───────────────────────────────────────▼─────────┐  │   │
│  │  │               WebSocket  /ws/{client_id}               │  │   │
│  │  └──────┬────────────────────────────────────────────────┘  │   │
│  │         │ FORENSIC_UPDATE / KILL_SWITCH_TRIGGERED             │   │
│  │  ┌──────▼─────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐  │   │
│  │  │ RiskMeter  │ │LegalAudit │ │FraudNetwork│ │CrimeMap  │  │   │
│  │  └────────────┘ └───────────┘ └────────────┘ └──────────┘  │   │
│  │  ┌────────────┐ ┌───────────┐ ┌─────────────────────────┐  │   │
│  │  │ForensicSigs│ │Interv.Log │ │   CaseHistory           │  │   │
│  │  └────────────┘ └───────────┘ └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / WS
┌──────────────────────────────▼──────────────────────────────────────┐
│                        FastAPI Backend (uvicorn)                     │
│  POST /analyze    →  BehavioralClassifier + ProtocolVerifier         │
│                      + LegalRAG + InterventionService (conditional)  │
│                      + DB persist + WS broadcast                     │
│  POST /analyze-document  →  VisionForensics                          │
│  POST /analyze-currency  →  CurrencyVerifier                         │
│  GET  /cases             →  SQLite CaseReport query                  │
│  GET  /metrics           →  EvaluationFramework                      │
│  WS   /ws/{client_id}    →  ConnectionManager broadcast              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ SQLAlchemy ORM
┌──────────────────────────────▼──────────────────────────────────────┐
│                     SQLite  bharat_kavach.db                         │
│   Tables: case_reports, forensic_documents                           │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow — Transcript Analysis with Auto-Intervention

```
Officer types transcript
        │
        ▼
TranscriptPanel.handleSubmit()
        │  POST /analyze  {transcript, user_id}
        ▼
main.py:analyze_call()
   ├─ BehavioralClassifier.analyze_transcript()  → AnalysisResult
   ├─ ProtocolVerifier.check_violations()        → violations[]
   ├─ LegalRAG.verify_legal_claims()             → LegalClaim[]
   ├─ risk_score = analysis.confidence * 100
   ├─ if risk_score > 85 AND stage == "Financial Demand / UPI Request":
   │      InterventionService.trigger_kill_switch()
   │      broadcast KILL_SWITCH_TRIGGERED
   ├─ CaseReport.save(DB)
   └─ broadcast FORENSIC_UPDATE
        │
        ▼
Dashboard WebSocket handler updates:
  caseData.score, .stage, .findings, .signals
  FraudNetwork re-fetches /cases
  CrimeMap re-renders pins from updated cases prop
```

---

## Components and Interfaces

### Backend Components

#### 1. `database.py` — Bug Fix (Req 1)

**Problem:** Line 1 imports `create_dotenv` from `sqlalchemy`, which does not exist.

**Fix:**
```python
# BEFORE (broken)
from sqlalchemy import create_dotenv, create_engine, Column, ...

# AFTER (fixed)
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON
```

No other changes needed. The rest of `database.py` is correct. The `get_db()` generator and both ORM models (`CaseReport`, `ForensicDocument`) are already well-formed.

---

#### 2. `main.py` — Auto-Intervention + `/metrics` Endpoint (Req 5, Req 10)

**Import path bug fix:** The existing import `from ai_engines.intervention import InterventionService` will fail because `InterventionService` lives in `backend/services/intervention.py`. Fix:

```python
from services.intervention import InterventionService
```

**`/analyze` changes for Req 5 — conditional kill-switch:**

```python
# After computing risk_score and stage:
intervention_triggered = False
intervention_result = None
intervention_error = None

KILL_SWITCH_STAGE = "Financial Demand / UPI Request"
if risk_score > 85 and stage == KILL_SWITCH_STAGE:
    try:
        result = InterventionService.trigger_kill_switch(
            scam_type="Digital Arrest",
            victim_id=request.user_id
        )
        intervention_triggered = True
        intervention_result = result
        new_case.interventions = result["actions_taken"]  # persisted to DB
        # broadcast KILL_SWITCH_TRIGGERED
        await manager.broadcast(json.dumps({
            "type": "KILL_SWITCH_TRIGGERED",
            "data": {
                "actions_taken": result["actions_taken"],
                "incident_id": result["incident_id"],
                "risk_score": risk_score,
                "stage": stage,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }))
    except Exception as e:
        logger.exception("Intervention failed")
        intervention_error = f"Intervention failed: {str(e)}"
        new_case.interventions = []
```

**`/metrics` endpoint for Req 10:**

```python
@app.get("/metrics")
async def get_metrics():
    if MOCK_MODE:
        return {
            "total_samples": 40, "precision": 0.93, "recall": 0.91,
            "false_positive_rate": 0.04,
            "confusion_matrix": {"tp": 27, "tn": 10, "fp": 1, "fn": 2},
            "mode": "mock"
        }
    try:
        from tests.eval_metrics import EvaluationFramework, TEST_CASES
        framework = EvaluationFramework(api_key=GOOGLE_API_KEY)
        results = framework.run_eval(TEST_CASES)
        metrics = framework.calculate_metrics(results)
        metrics["mode"] = "live"
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
```

The 40-sample `test_cases` list in `eval_metrics.py` must be extracted into a module-level constant `TEST_CASES` so it can be imported by `main.py`.

#### 3. `backend/tests/eval_metrics.py` — EvaluationFramework Fix (Req 10)

The existing file has one field name bug: `beh_analysis.risk_score` does not exist on `AnalysisResult`. The correct field is `confidence`, scaled to `confidence * 100`.

**Fix in `run_eval()`:**
```python
# BEFORE (broken)
prediction = "scam" if (beh_analysis.risk_score > 60 ...) else "legit"

# AFTER (fixed)
risk_score = beh_analysis.confidence * 100
prediction = "scam" if (risk_score > 60 or myths_found or len(violations) > 0) else "legit"
```

The 40-sample list must be promoted to a module-level constant:
```python
TEST_CASES = [
    {"id": "scam_1", "label": "scam", "transcript": "..."},
    # ... all 40 entries ...
]
```

`calculate_metrics()` must add `"mode"` key before returning so the `/metrics` endpoint can override it.

---

### Frontend Components

#### 4. `TranscriptPanel.jsx` — New component (Req 2)

**File:** `frontend/src/components/dashboard/TranscriptPanel.jsx`

**Props:** `onResult(data)` — called with the HTTP response body after a successful `/analyze` call.

**Internal state:**
- `transcript: string` — controlled textarea value
- `loading: boolean` — POST in-flight flag
- `error: string | null` — validation or network error text

**Behavior:**
- Textarea: `maxLength={10000}`, placeholder "Paste conversation transcript here..."
- Submit: validates non-empty (after `.trim()`), sets `loading=true`, POSTs `{transcript, user_id: "OFFICER_001"}` to `http://localhost:8000/analyze` with a 30-second `AbortController` timeout.
- On success: calls `onResult(data)`, clears error.
- On failure (network, ≥400, timeout): sets error "Analysis failed. Please try again.", re-enables button.
- Validation failure (empty): sets error "Transcript cannot be empty", no POST.
- While loading: button shows spinner and is `disabled`.

**Dashboard wiring:** `Dashboard.jsx` passes `onResult` that updates no additional state beyond what the WebSocket already provides — the WS `FORENSIC_UPDATE` is the primary state update path. The HTTP response body (`{id, status}`) is minimal.

---

#### 5. `DocumentPanel.jsx` — New component (Req 3)

**File:** `frontend/src/components/dashboard/DocumentPanel.jsx`

**Internal state:**
- `file: File | null`
- `loading: boolean`
- `result: object | null` — raw `/analyze-document` response
- `error: string | null`

**Accepted MIME types:** `image/jpeg`, `image/png`, `application/pdf` (max 10 MB enforced client-side via `file.size > 10 * 1024 * 1024`).

**Result rendering:**
- Verdict string: displayed as-is.
- Confidence: `Math.round(result.confidence_score * 100) + "%"`.
- Explanation string: rendered in a `<p>`.
- `forensic_signals`: iterate `Object.entries(result.forensic_signals)` and render each key as a labeled `<div>` with a bar whose width is `Math.round(value * 100) + "%"`.
- High-forgery alert: if `result.verdict.includes("Fake") && result.confidence_score >= 0.75`, render result container with `border-red-500` and text "HIGH FORGERY CONFIDENCE".

---

#### 6. `CurrencyPanel.jsx` — New component (Req 4)

**File:** `frontend/src/components/dashboard/CurrencyPanel.jsx`

**Internal state:** `file`, `loading`, `result`, `error` (same pattern as DocumentPanel).

**Accepted MIME types:** `image/jpeg`, `image/png` only.

**Result rendering:**
- `"Note Type: " + result.note_type`
- Thread: `result.signals.thread_detected ? "Security Thread: Detected" : "Security Thread: Not Detected"`
- Reason (if present): `"Reason: " + result.signals.reason`
- Badge: `result.signals.is_suspicious` → red badge "SUSPICIOUS NOTE DETECTED", else green badge "NOTE APPEARS GENUINE".

**Loading behavior:** clears previous `result` to `null` at the moment of submission (prevents stale display).

#### 7. `FraudNetwork.jsx` — Live Data Wiring (Req 6)

**File:** `frontend/src/components/forensics/FraudNetwork.jsx` (replace existing)

**Props:** `cases: array` — list of CaseReport objects passed from Dashboard state, OR the component fetches internally and accepts a `refreshTrigger` prop (boolean toggled by parent on FORENSIC_UPDATE).

**Design decision:** FraudNetwork receives `cases` as a prop from Dashboard. Dashboard already fetches `/cases` on mount and stores in `caseData.history`. On `FORENSIC_UPDATE`, Dashboard re-fetches `/cases` and updates `caseData.history`. FraudNetwork is a pure rendering component over that prop.

**Node extraction algorithm:**
```javascript
const PHONE_REGEX = /[6-9]\d{9}/g;

function deriveNetwork(cases) {
  const highRisk = cases.filter(c => c.risk_score > 70);
  if (highRisk.length === 0) return null;

  // Primary Suspect: highest timestamp, tiebreak by largest id
  const primary = highRisk.reduce((best, c) => {
    const tBest = new Date(best.timestamp).getTime();
    const tC = new Date(c.timestamp).getTime();
    if (tC > tBest) return c;
    if (tC === tBest) return c.id > best.id ? c : best;
    return best;
  });

  // Phone nodes from all contributing cases
  const phoneSet = new Set();
  const contributingIds = new Set([primary.id]);
  cases.forEach(c => {
    const matches = (c.transcript || "").match(PHONE_REGEX) || [];
    if (matches.length > 0) contributingIds.add(c.id);
    matches.forEach(p => phoneSet.add(p));
  });

  return {
    primary,
    phones: [...phoneSet],
    linkedCount: contributingIds.size
  };
}
```

**Layout:** Primary Suspect node at SVG center (200, 150). Phone nodes distributed in a circle at radius 90px using `cos/sin` with equal angular spacing. Edges drawn from center to each phone node using existing `Connection` component.

**Empty state:** If `cases` fetch fails, render "Network data unavailable" (hide static nodes). If no high-risk cases, render "No high-risk cases detected".

**Badge:** `"{linkedCount} CASES LINKED"` replacing the static "CLUSTERING ACTIVE".

---

#### 8. `CrimeMap.jsx` — India SVG + Dynamic Hotspots (Req 7)

**File:** `frontend/src/components/forensics/CrimeMap.jsx` (replace existing)

**Props:** `cases: array` — received from Dashboard (same `caseData.history` prop).

**India SVG approach:** Embed a simplified outline as an inline SVG path within a `500×580` viewBox. The path covers the recognizable coastline and major state outlines. This avoids external library dependencies (no D3, no topojson).

**City coordinate lookup table (SVG coordinates within 500×580 viewBox):**
```javascript
const CITY_COORDS = {
  "Delhi":     { x: 220, y: 120 },
  "Mumbai":    { x: 130, y: 280 },
  "Bangalore": { x: 195, y: 390 },
  "Chennai":   { x: 250, y: 410 },
  "Kolkata":   { x: 340, y: 210 },
  "Hyderabad": { x: 220, y: 330 },
  "Pune":      { x: 145, y: 300 },
  "Ahmedabad": { x: 110, y: 200 },
};
```

**Pin grouping:**
```javascript
function groupByCity(cases) {
  const groups = {};
  cases.forEach(c => {
    if (c.city && CITY_COORDS[c.city]) {
      groups[c.city] = (groups[c.city] || 0) + 1;
    }
  });
  return groups;  // { "Delhi": 3, "Mumbai": 1, ... }
}
```

**Pin color logic:**
```javascript
function pinColor(count) {
  if (count >= 5) return "#ef4444";  // red — Critical
  if (count >= 2) return "#f97316";  // orange — High
  return "#eab308";                   // yellow — Medium
}
```

**Pin animation:** Framer Motion `animate={{ scale: [1, 1.4, 1] }}` with `transition={{ repeat: Infinity, duration: 2 }}`. A `<circle>` with `animate={{ r: [6, 16, 6], opacity: [0.6, 0, 0.6] }}` creates the pulse halo effect within 2 seconds.

**Empty/error states:** Render India SVG outline regardless. If `cases` is empty → "No incidents reported" below map. If fetch error → "Data unavailable" below map. Timeout enforced in Dashboard fetch with `AbortController` at 10 seconds.

**Note:** The `CaseReport` ORM model currently has no `city` field. The `/cases` endpoint response will return `null` for city until the field is added. The CrimeMap must handle `city === null` gracefully (skip the record). Adding the `city` column to `CaseReport` is part of the implementation tasks.

#### 9. `CitizenApp.jsx` — Multilingual + Real API Calls (Req 8)

**File:** `frontend/src/components/dashboard/CitizenApp.jsx` (replace existing)

**Translation maps (static, embedded in component file):**

```javascript
const TRANSLATIONS = {
  en: {
    alertTitle: "Bharat Kavach Intelligence Alert",
    stagePrefix: "Scam Stage:",
    reportBtn: "REPORT",
    helplineBtn: "CALL 1930",
    safeMessage: "✓ Message appears safe. Stay cautious.",
    offlineFallback: "Could not analyze. Please call 1930 immediately.",
    unknownStage: "Scam detected",
  },
  hi: {
    alertTitle: "भारत कवच खुफिया अलर्ट",
    stagePrefix: "घोटाले का चरण:",
    reportBtn: "रिपोर्ट करें",
    helplineBtn: "1930 पर कॉल करें",
    safeMessage: "✓ संदेश सुरक्षित लगता है। सावधान रहें।",
    offlineFallback: "विश्लेषण नहीं हो सका। तुरंत 1930 पर कॉल करें।",
    unknownStage: "धोखाधड़ी पहचानी गई",
  },
  ta: {
    alertTitle: "பாரத் கவச் புலனாய்வு எச்சரிக்கை",
    stagePrefix: "மோசடி நிலை:",
    reportBtn: "புகாரளி",
    helplineBtn: "1930 அழை",
    safeMessage: "✓ செய்தி பாதுகாப்பானது. கவனமாக இருங்கள்.",
    offlineFallback: "பகுப்பாய்வு முடியவில்லை. உடனே 1930 அழையுங்கள்.",
    unknownStage: "மோசடி கண்டறியப்பட்டது",
  },
};
```

**Language selector:** Three buttons (EN / हिन्दी / தமிழ்) rendered above the chat window. Active language stored in `language` state, defaulting to `"en"`.

**`sendMessage()` logic:**
```javascript
const sendMessage = async () => {
  if (!input.trim()) return;
  const userMsg = { id: Date.now(), text: input, sender: "me" };
  setMessages(prev => [...prev, userMsg]);
  setInput("");
  setLoading(true);
  setAlertState(null);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch("http://localhost:8000/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript: input }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const data = await res.json();
    const score = data.risk_score ?? (data.confidence * 100);
    setAlertState({ score, stage: data.stage });
  } catch {
    clearTimeout(timeoutId);
    setAlertState({ offline: true });
  } finally {
    setLoading(false);
  }
};
```

**Alert banner rendering:** Conditionally renders below the message area based on `alertState`:
- `alertState.offline` → offline fallback text in selected language.
- `alertState.score >= 60` → red alert banner with stage label (translated), REPORT button, CALL 1930 button.
- `alertState.score < 60` → green safe-message confirmation.

**Typing indicator:** While `loading` is true, append a bubble `{ id: "typing", text: "...", sender: "typing" }` to messages. The bubble renders three animated dots using Framer Motion `animate={{ opacity: [0.3, 1, 0.3] }}` with `staggerChildren`.

---

#### 10. Dashboard Export — Intelligence Package (Req 9)

**No new file needed.** The export logic is added to `Dashboard.jsx` as a `handleExport()` function.

```javascript
const handleExport = () => {
  if (caseData.score === 0) {
    setToast("No active case to export. Analyze a transcript first.");
    return;
  }
  const now = new Date();
  const ts = now.toISOString().replace(/[-:]/g, "").split(".")[0]; // yyyyMMddTHHmmss
  const caseId = caseData.id ?? "UNKNOWN";

  const pkg = {
    case_id: caseId,
    transcript: caseData.transcript ?? "",
    risk_score: caseData.score,
    stage: caseData.stage,
    legal_findings: caseData.findings ?? [],
    interventions: caseData.interventions ?? [],
    exported_at: now.toISOString(),
  };

  // Conditional intervention_result
  const withIncident = (caseData.interventions ?? []).find(i => i.incident_id);
  if (withIncident) {
    pkg.intervention_result = {
      actions_taken: withIncident.actions_taken ?? [],
      incident_id: withIncident.incident_id,
      triggered_at: withIncident.timestamp ?? now.toISOString(),
    };
  }

  const blob = new Blob([JSON.stringify(pkg, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `bharat-kavach-case-${caseId}-${ts}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
```

**Toast notification:** `toast` state (string | null). When non-null, render a fixed bottom-center `<div>` with auto-dismiss via `setTimeout(() => setToast(null), 3000)`.

**Dashboard state additions needed:**
- `caseData.id` — populated from WebSocket `FORENSIC_UPDATE` message (`message.data.id`)
- `caseData.transcript` — populated from the TranscriptPanel submission (stored locally before POST)

#### 11. Dashboard Grid Reorganization (Req 2, 3, 4, 12)

The current 12-column grid has three sections: `col-span-3` (RiskMeter + CaseHistory), `col-span-5` (CrimeMap + FraudNetwork), `col-span-4` (LegalAudit + InterventionLog).

**Updated layout (1280px viewport, no horizontal scroll):**

```
┌─────────────────────────────────────────────────────────────────────┐
│ col-span-3               │ col-span-5                │ col-span-4   │
│ RiskMeter                │ TranscriptPanel (h-auto)  │ ForensicSigs │
│ ForensicSignals          │ CrimeMap        (h-350px) │ LegalAudit   │
│ CaseHistory   (h-400px)  │ FraudNetwork    (h-350px) │ InterventionLog│
│                          │ DocumentPanel   (h-auto)  │              │
│                          │ CurrencyPanel   (h-auto)  │              │
└─────────────────────────────────────────────────────────────────────┘
```

**ForensicSignals placement:** Moved from "not rendered" to the `col-span-3` left column, between RiskMeter and CaseHistory. It receives `signals={caseData.signals}`.

**Right column `col-span-4`:** Retains LegalAudit and InterventionLog. ForensicSignals moves to left column to avoid overflow in the right column.

**`caseData.signals` update logic on `FORENSIC_UPDATE`:**
```javascript
const hasFalseFindings = (findings) =>
  Array.isArray(findings) && findings.some(f => f.verdict === "confirmed_false");

setCaseData(prev => ({
  ...prev,
  id: message.data.id,
  score: message.data.score,
  stage: message.data.stage,
  findings: message.data.findings,
  signals: {
    behavioral: message.data.score,
    legal: hasFalseFindings(message.data.findings) ? 0 : 100,
    vision: prev.signals.vision,    // unchanged until document analysis
    protocol: prev.signals.protocol // unchanged until protocol violation
  }
}));
```

**`caseData.signals` update on `KILL_SWITCH_TRIGGERED`:**
```javascript
setCaseData(prev => ({
  ...prev,
  interventions: [
    ...prev.interventions,
    {
      type: "FINANCIAL",
      action: message.data.actions_taken[0],
      details: message.data.incident_id,
      timestamp: message.data.timestamp,
      incident_id: message.data.incident_id,
      actions_taken: message.data.actions_taken,
    }
  ]
}));
```

---

#### 12. `.env.example` (Req 11)

**File:** `bharat-kavach/.env.example`

```dotenv
# Bharat Kavach — Environment Configuration
# Copy this file to .env and populate the values before starting the backend server.
# Run: cp .env.example .env

# Required: Google Gemini API key for Gemini 1.5 Flash AI features.
# Obtain from: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here
```

**`.gitignore` check:** The existing `.gitignore` must contain `.env` (not `.env.example`). Verify and add the line if missing.

---

## Data Models

### Backend — CaseReport (extended for Req 5 + Req 7)

```python
class CaseReport(Base):
    __tablename__ = "case_reports"
    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(String, index=True)
    transcript    = Column(String)
    risk_score    = Column(Float)
    stage         = Column(String)
    verdict       = Column(String)
    legal_citations = Column(JSON)   # List[LegalClaim.dict()]
    interventions = Column(JSON)     # List[str] — action names, e.g. ["UPI_HOLD"]
    city          = Column(String, nullable=True)  # NEW — for CrimeMap hotspots
    timestamp     = Column(DateTime, default=datetime.datetime.utcnow)
```

**Migration note:** Adding `city` column to SQLite requires a schema migration. Since SQLite supports `ALTER TABLE ADD COLUMN`, this can be done via an Alembic migration or by dropping and recreating `bharat_kavach.db` during development. For the hackathon demo, a startup-time migration guard is sufficient:

```python
# In database.py, after Base.metadata.create_all(bind=engine)
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE case_reports ADD COLUMN city VARCHAR"))
        conn.commit()
except Exception:
    pass  # Column already exists
```

### `/analyze` Request Model

```python
class TranscriptRequest(BaseModel):
    transcript: str
    user_id: Optional[str] = "DEMO_USER_001"
    city: Optional[str] = None  # NEW — passed from frontend if known
```

### `/analyze` Response Model (extended for Req 5)

```json
{
  "id": 42,
  "status": "SAVED",
  "risk_score": 91.2,
  "stage": "Financial Demand / UPI Request",
  "legal_citations": [...],
  "intervention_triggered": true,
  "intervention_result": {
    "actions_taken": ["UPI_HOLD", "TELECOM_FLAG", "POLICE_ALERT"],
    "incident_id": "BK-1720000000"
  }
}
```

### WebSocket Message Types

**`FORENSIC_UPDATE`** (broadcast after every `/analyze` call):
```json
{
  "type": "FORENSIC_UPDATE",
  "data": {
    "id": 42,
    "score": 91.2,
    "stage": "Financial Demand / UPI Request",
    "findings": [{"claim_extracted": "...", "verdict": "confirmed_false", "explanation": "..."}]
  }
}
```

**`KILL_SWITCH_TRIGGERED`** (broadcast only when intervention fires):
```json
{
  "type": "KILL_SWITCH_TRIGGERED",
  "data": {
    "actions_taken": ["UPI_HOLD", "TELECOM_FLAG", "POLICE_ALERT"],
    "incident_id": "BK-1720000000",
    "risk_score": 91.2,
    "stage": "Financial Demand / UPI Request",
    "timestamp": "2024-07-04T10:30:00Z"
  }
}
```

### `/metrics` Response Model

```json
{
  "total_samples": 40,
  "precision": 0.9375,
  "recall": 0.9000,
  "false_positive_rate": 0.0400,
  "confusion_matrix": { "tp": 27, "tn": 9, "fp": 1, "fn": 3 },
  "mode": "live"
}
```

### Intelligence Package Export Schema

```json
{
  "case_id": 42,
  "transcript": "Inspector Rathore speaking...",
  "risk_score": 91.2,
  "stage": "Financial Demand / UPI Request",
  "legal_findings": [...],
  "interventions": ["UPI_HOLD", "TELECOM_FLAG", "POLICE_ALERT"],
  "exported_at": "2024-07-04T10:30:00.000Z",
  "intervention_result": {
    "actions_taken": ["UPI_HOLD", "TELECOM_FLAG", "POLICE_ALERT"],
    "incident_id": "BK-1720000000",
    "triggered_at": "2024-07-04T10:29:58.000Z"
  }
}
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Non-empty transcript always triggers a POST

*For any* non-empty, non-whitespace-only string entered as a transcript in the TranscriptPanel or CitizenApp, submitting the input SHALL result in exactly one POST request being dispatched to `/analyze`.

**Validates: Requirements 2.2, 8.2**

---

### Property 2: FORENSIC_UPDATE message drives all Dashboard state fields

*For any* valid `FORENSIC_UPDATE` WebSocket message with fields `{score, stage, findings, id}`, the Dashboard SHALL update `caseData.score`, `caseData.stage`, `caseData.findings`, `caseData.id`, and all four `caseData.signals` fields according to the specified mapping rules.

**Validates: Requirements 2.3, 2.4, 2.5, 12.2**

---

### Property 3: Forgery alert threshold is correctly applied

*For any* `/analyze-document` response object, the DocumentPanel SHALL render a high-forgery alert (red border + "HIGH FORGERY CONFIDENCE" text) if and only if `verdict.includes("Fake") === true` AND `confidence_score >= 0.75`. For all other combinations, the alert SHALL NOT be rendered.

**Validates: Requirements 3.5**

---

### Property 4: Document forensic signals render as proportional progress bars

*For any* `forensic_signals` object returned by `/analyze-document`, the DocumentPanel SHALL render one labeled progress bar for each key, where the bar's display width percentage equals `Math.round(value * 100)` for that key's value.

**Validates: Requirements 3.4**

---

### Property 5: Currency suspicion badge is correctly toggled

*For any* `/analyze-currency` response, the CurrencyPanel SHALL render a red "SUSPICIOUS NOTE DETECTED" badge if and only if `signals.is_suspicious === true`, and a green "NOTE APPEARS GENUINE" badge if and only if `signals.is_suspicious === false`.

**Validates: Requirements 4.4, 4.5**

---

### Property 6: Kill-switch fires iff both threshold conditions are met

*For any* transcript submitted to `/analyze`, the backend SHALL call `InterventionService.trigger_kill_switch()` if and only if the computed `risk_score > 85` AND `stage === "Financial Demand / UPI Request"`. For any other (risk_score, stage) combination, the kill-switch SHALL NOT be called.

**Validates: Requirements 5.1, 5.6**

---

### Property 7: Intervention data persists to DB and appears in HTTP response

*For any* qualifying `/analyze` call (risk_score > 85 and correct stage) where `trigger_kill_switch()` returns successfully, the resulting `CaseReport` row SHALL have a non-empty `interventions` JSON field, and the HTTP response SHALL contain `intervention_triggered: true` and an `intervention_result` object with `actions_taken` and `incident_id`.

**Validates: Requirements 5.2, 5.3**

---

### Property 8: FraudNetwork primary suspect selection is deterministic

*For any* list of cases, the FraudNetwork's primary suspect SHALL be the case with `risk_score > 70` having the latest `timestamp` (with `id` as tiebreaker). If no such case exists, the component SHALL render "No high-risk cases detected".

**Validates: Requirements 6.2, 6.4**

---

### Property 9: Phone number extraction is regex-complete

*For any* transcript string, the FraudNetwork phone-number extraction SHALL include every 10-digit sequence matching `[6-9]\d{9}` and SHALL NOT include sequences that do not match this pattern.

**Validates: Requirements 6.1, 6.3**

---

### Property 10: CrimeMap pin color matches case-count thresholds

*For any* city with N cases, the CrimeMap SHALL render its pin in red (`#ef4444`) when N ≥ 5, orange (`#f97316`) when 2 ≤ N ≤ 4, and yellow (`#eab308`) when N = 1.

**Validates: Requirements 7.4**

---

### Property 11: CitizenApp alert language is always consistent with selected language

*For any* `/analyze` response with `risk_score >= 60` and any selected language (en/hi/ta), the CitizenApp SHALL display the alert title, stage prefix, report button label, and helpline button label drawn exclusively from the translation map for the selected language.

**Validates: Requirements 8.3, 8.5, 8.7**

---

### Property 12: Intelligence package export contains exactly the required fields

*For any* `caseData` with `score > 0`, the exported JSON file SHALL be parseable by `JSON.parse()` and SHALL contain exactly the keys `case_id`, `transcript`, `risk_score`, `stage`, `legal_findings`, `interventions`, `exported_at`. When `caseData.interventions` contains an entry with an `incident_id`, the package SHALL additionally contain an `intervention_result` object; otherwise that key SHALL be absent.

**Validates: Requirements 9.1, 9.2, 9.3, 9.5**

---

### Property 13: Translation map completeness

*For any* language key in `TRANSLATIONS` (en, hi, ta), all seven required keys (`alertTitle`, `stagePrefix`, `reportBtn`, `helplineBtn`, `safeMessage`, `offlineFallback`, `unknownStage`) SHALL be present and non-empty strings.

**Validates: Requirements 8.7**

---

### Property 14: ForensicSignals Alert state tracks behavioral and legal thresholds

*For any* `signals.behavioral` value, the ForensicSignals component SHALL render the "Behavioral Arc" bar with `status="Alert"` if and only if `behavioral > 60`. *For any* `signals.legal` value, the component SHALL render the "Legal Grounding" bar with `status="Alert"` if and only if `legal < 50`.

**Validates: Requirements 12.3, 12.4**

---

## Error Handling

### Backend Error Handling

| Scenario | Behavior |
|---|---|
| `database.py` import error | Fixed by removing `create_dotenv`. No runtime handler needed. |
| `BehavioralClassifier` raises exception | Returns `AnalysisResult(confidence=0.0, ...)` — already handled in `behavioral.py`. |
| `LegalRAG` raises exception | Returns `[]` — already handled in `legal_rag.py`. |
| `InterventionService.trigger_kill_switch()` raises | Log exception, set `intervention_triggered=false`, include `intervention_error` in response, save CaseReport with empty interventions. |
| `/analyze-document` — invalid image bytes | `cv2.imdecode` returns `None`; return HTTP 422 with `detail: "Invalid image data"`. |
| `/analyze-currency` — invalid image bytes | Same as above, return HTTP 422. |
| `EvaluationFramework` raises in `/metrics` | Return HTTP 500 with `detail: "{ExceptionType}: {message}"`. |
| WebSocket client disconnects mid-broadcast | `ConnectionManager.broadcast()` must catch `WebSocketDisconnect` per connection and remove it; do not abort the broadcast loop. Current implementation iterates `active_connections` and may raise — needs a try/except per connection. |

**ConnectionManager broadcast fix:**
```python
async def broadcast(self, message: str):
    dead = []
    for connection in self.active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            dead.append(connection)
    for d in dead:
        self.active_connections.remove(d)
```

### Frontend Error Handling

| Component | Error Scenario | Displayed Message |
|---|---|---|
| TranscriptPanel | Empty input | "Transcript cannot be empty" |
| TranscriptPanel | POST fails / timeout | "Analysis failed. Please try again." |
| DocumentPanel | No file selected | "Please select a document to analyze" |
| DocumentPanel | Wrong MIME type | "Unsupported file type. Please upload a JPEG, PNG, or PDF." |
| DocumentPanel | POST fails / timeout | "Document analysis failed. Please try again." |
| CurrencyPanel | No file selected | "Please select a currency image to verify" |
| CurrencyPanel | Wrong MIME type | "Unsupported file type. Please upload a JPEG or PNG image." |
| CurrencyPanel | POST fails / timeout | "Currency verification failed. Please try again." |
| CitizenApp | POST fails / 10s timeout | Offline fallback alert in selected language |
| FraudNetwork | `/cases` fetch fails | "Network data unavailable" (hide static nodes) |
| CrimeMap | `/cases` fetch fails | India SVG outline + "Data unavailable" |
| CrimeMap | `/cases` returns empty | India SVG outline + "No incidents reported" |
| Dashboard export | `caseData.score === 0` | Toast: "No active case to export. Analyze a transcript first." |

All error messages self-clear when the user retries or navigates away. No automatic retry logic — users must re-submit manually.

---

## Testing Strategy

### Unit Tests — Backend

**Framework:** `pytest` (already in use via `backend/tests/`)

**Test file additions:**

1. `backend/tests/test_database.py`
   - Smoke test: `import database` completes without `ImportError` — verifies Req 1.1.
   - Smoke test: Both tables (`case_reports`, `forensic_documents`) exist after `create_all` — verifies Req 1.3.

2. `backend/tests/test_analyze_endpoint.py`
   - Example test: Mock `BehavioralClassifier`, `LegalRAG`, `InterventionService`. POST to `/analyze` with `risk_score > 85` + correct stage → assert `intervention_triggered: true` in response and `interventions` non-empty in DB row.
   - Example test: Same mocks, `risk_score > 85` but wrong stage → assert `intervention_triggered: false`, no `trigger_kill_switch` call.
   - Example test: `InterventionService` raises → assert HTTP 200 with `intervention_triggered: false` and `intervention_error` key.

3. `backend/tests/test_metrics.py`
   - Example test: Call `GET /metrics` in mock mode → assert all six required fields present and `mode == "mock"`.
   - Example test: `EvaluationFramework.calculate_metrics()` with known confusion matrix → assert precision/recall math is correct.

4. **Property tests** (using `hypothesis`):
   - Property 6 (kill-switch threshold): Generate `(confidence: float[0,1], stage: str)` pairs using `@given`. Assert `trigger_kill_switch` is called iff `confidence * 100 > 85 and stage == "Financial Demand / UPI Request"`.
   - Property 7 (DB persistence): Generate qualifying inputs, run `/analyze` via TestClient, read CaseReport from test DB, assert `interventions` non-empty.

### Unit Tests — Frontend

**Framework:** Vitest + React Testing Library (standard for React 19 / Vite projects)

**No test framework currently exists** — `package.json` has no test script. Add:
```json
"scripts": {
  "test": "vitest --run"
},
"devDependencies": {
  "vitest": "^1.6.0",
  "@testing-library/react": "^16.0.0",
  "@testing-library/user-event": "^14.5.2",
  "jsdom": "^24.1.0"
}
```

**Test file additions:**

1. `frontend/src/components/dashboard/__tests__/TranscriptPanel.test.jsx`
   - Example: renders panel, textarea, and ANALYZE button.
   - Property 1: use `fc.string({ minLength: 1 })` from `fast-check` to generate non-empty transcripts; mock `fetch`; assert POST called for each.
   - Property 2 (partial): verify FORENSIC_UPDATE WebSocket payload updates state correctly.
   - Edge case: empty/whitespace input → no POST, error message shown.

2. `frontend/src/components/dashboard/__tests__/DocumentPanel.test.jsx`
   - Property 3: use `fc` to generate verdict strings and confidence values; assert forgery alert shown iff `verdict.includes("Fake") && confidence >= 0.75`.
   - Property 4: generate random `forensic_signals` dicts; assert each key rendered as a progress bar.

3. `frontend/src/components/dashboard/__tests__/CurrencyPanel.test.jsx`
   - Property 5: generate `is_suspicious: true/false`; assert correct badge color and text.

4. `frontend/src/components/forensics/__tests__/FraudNetwork.test.jsx`
   - Property 8: generate case arrays with varying `risk_score` and `timestamp`; assert correct primary suspect.
   - Property 9: generate transcripts with phone numbers; assert all matching numbers extracted.

5. `frontend/src/components/forensics/__tests__/CrimeMap.test.jsx`
   - Property 10: generate case counts per city; assert correct pin color for each count range.

6. `frontend/src/components/dashboard/__tests__/CitizenApp.test.jsx`
   - Property 11: generate `risk_score` values ≥ 60 and language selections; assert alert text in correct language.
   - Property 13: static assertion that all 7 keys are non-empty in all 3 translation objects.

7. `frontend/src/components/dashboard/__tests__/Dashboard.test.jsx`
   - Property 12: generate `caseData` with `score > 0`; call `handleExport`; parse the blob URL content; assert exactly 7 fields (+ conditional `intervention_result`).
   - Property 14: generate `behavioral` and `legal` values; render ForensicSignals; assert Alert/Normal/Secure labels.

### Property-Based Testing Library

**Backend:** `hypothesis` (Python) — add to `backend/requirements.txt`.
**Frontend:** `fast-check` — add to `frontend/package.json` devDependencies.

Each property test runs minimum 100 iterations. Tag format:
```
// Feature: bharat-kavach-complete, Property 1: non-empty transcript triggers POST
```

### Integration Tests

- Start the backend with `TestClient` from `fastapi.testclient` (synchronous, no real uvicorn needed).
- Use an in-memory SQLite override (`SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"`).
- Test the full `/analyze` → DB persist → WS broadcast chain end-to-end.
- Test `/metrics` in mock mode (no Gemini calls).

### What Cannot Be Verified Automatically

- Visual appearance of the India SVG outline (requires visual regression testing).
- Pulse animation timing (Framer Motion animation timing — manual verification).
- WebSocket real-time latency under concurrent connections.
- Actual Gemini API responses (depend on external service; covered by MOCK_MODE).

---

## File-Level Implementation Plan

This section maps each requirement to the exact files that need to be created or modified.

### Files to Modify

| File | Changes | Requirement(s) |
|---|---|---|
| `backend/database.py` | Remove `create_dotenv` from import; add `city` column to `CaseReport`; add startup migration guard | 1, 7 |
| `backend/main.py` | Fix `InterventionService` import path; add kill-switch logic to `/analyze`; extend response model; add `GET /metrics` endpoint; fix `ConnectionManager.broadcast()` | 5, 10 |
| `backend/tests/eval_metrics.py` | Fix `beh_analysis.risk_score` → `beh_analysis.confidence * 100`; promote `test_cases` list to `TEST_CASES` module constant; add `mode` key to `calculate_metrics()` return | 10 |
| `frontend/src/components/dashboard/Dashboard.jsx` | Add `TranscriptPanel`, `DocumentPanel`, `CurrencyPanel` to imports and JSX; render `ForensicSignals` in left column; update grid layout; add `handleExport()`; add toast state; update WebSocket handler to populate all signals and handle `KILL_SWITCH_TRIGGERED`; add `caseData.id` and `caseData.transcript` to state; pass `cases={caseData.history}` to FraudNetwork and CrimeMap | 2, 3, 4, 5, 9, 12 |
| `frontend/src/components/forensics/FraudNetwork.jsx` | Replace static hardcoded nodes with dynamic data from `cases` prop; implement `deriveNetwork()`; add `N CASES LINKED` badge; add empty/error states | 6 |
| `frontend/src/components/forensics/CrimeMap.jsx` | Replace rect-grid SVG with India outline SVG; implement `groupByCity()` and `pinColor()`; fetch from `cases` prop; add city label + count labels; add pulsing animation; add empty/error states | 7 |
| `frontend/src/components/dashboard/CitizenApp.jsx` | Add language selector; add `TRANSLATIONS` map; replace static hardcoded alert with real `/analyze` POST; add `loading` state with typing indicator; add risk-based conditional alert rendering | 8 |
| `backend/requirements.txt` | Add `hypothesis` | 10 |
| `frontend/package.json` | Add `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`, `fast-check` to devDependencies; add `test` script | All |
| `.gitignore` (root) | Ensure `.env` is listed; ensure `.env.example` is NOT listed | 11 |

### Files to Create

| File | Purpose | Requirement(s) |
|---|---|---|
| `bharat-kavach/.env.example` | Documents all environment variables | 11 |
| `frontend/src/components/dashboard/TranscriptPanel.jsx` | Live transcript input + analyze button | 2 |
| `frontend/src/components/dashboard/DocumentPanel.jsx` | Document forensics upload + results | 3 |
| `frontend/src/components/dashboard/CurrencyPanel.jsx` | Currency verification upload + results | 4 |
| `frontend/src/components/dashboard/__tests__/TranscriptPanel.test.jsx` | Unit + property tests for TranscriptPanel | 2 |
| `frontend/src/components/dashboard/__tests__/DocumentPanel.test.jsx` | Unit + property tests for DocumentPanel | 3 |
| `frontend/src/components/dashboard/__tests__/CurrencyPanel.test.jsx` | Unit + property tests for CurrencyPanel | 4 |
| `frontend/src/components/forensics/__tests__/FraudNetwork.test.jsx` | Property tests for network derivation | 6 |
| `frontend/src/components/forensics/__tests__/CrimeMap.test.jsx` | Property tests for pin coloring | 7 |
| `frontend/src/components/dashboard/__tests__/CitizenApp.test.jsx` | Property tests for multilingual alerts | 8 |
| `frontend/src/components/dashboard/__tests__/Dashboard.test.jsx` | Property tests for export + signals | 9, 12 |
| `backend/tests/test_database.py` | Smoke tests for import fix + table creation | 1 |
| `backend/tests/test_analyze_endpoint.py` | Example + property tests for intervention logic | 5 |
| `backend/tests/test_metrics.py` | Example tests for /metrics endpoint | 10 |
| `frontend/vite.config.js` | Add vitest config block (`test: { environment: "jsdom" }`) | All |

### No Changes Needed

The following files are correct as-is and require no modification:

- `backend/ai_engines/behavioral.py` — `AnalysisResult` model is complete
- `backend/ai_engines/vision.py` — `VisionForensics` pipeline is complete
- `backend/ai_engines/currency.py` — `CurrencyVerifier` is complete
- `backend/ai_engines/legal_rag.py` — `LegalRAG` pipeline is complete
- `backend/ai_engines/protocol.py` — `ProtocolVerifier` is complete
- `backend/services/intervention.py` — `InterventionService` is complete
- `frontend/src/components/forensics/ForensicSignals.jsx` — Component is correct; just needs to be rendered in Dashboard
- `frontend/src/components/forensics/LegalAudit.jsx` — No changes needed
- `frontend/src/components/forensics/InterventionLog.jsx` — No changes needed
- `frontend/src/components/forensics/RiskMeter.jsx` — No changes needed
- `frontend/src/components/dashboard/CaseHistory.jsx` — No changes needed
