# Bharat Kavach: AI-Powered Digital Public Safety (v2.0 - Winner's Edition)

Bharat Kavach is a forensic AI platform that transitions from simple detection to **active intervention**. It uses behavioral intelligence to track scam escalation and triggers protective measures before financial loss occurs.

## User Review Required

> [!IMPORTANT]
> **Intervention Simulation**: The "Kill Switch" (Bank/UPI hold) will be a simulated webhook for the demo to show business impact without needing real bank integrations.
> **Dataset**: We will curate a test set of 40-50 samples (Scam vs. Legit) to report actual Precision/Recall numbers—a key requirement of the "Evaluation Focus" rubric.

## Proposed Changes

---

### Phase 1: The Behavioral & Forensic Engine

#### [NEW] [BehavioralClassifier.py](backend/ai_engines/behavioral.py)
*   **Old**: Keyword Matching.
*   **New**: **Conversation Stage Classifier**.
*   **Mechanism**: Uses an LLM to map live transcripts to the "Scam Arc":
    1.  **Authority Impersonation** (CBI/ED/Police)
    2.  **Digital Confinement/Isolation** ("Stay on the call," "Don't tell family")
    3.  **Fabricated Evidence** (Fake FIR/Parcel claims)
    4.  **Urgency/Fear Injection** (Threat of immediate arrest)
    5.  **Financial Extraction** (Demand for UPI/Security Deposit)

#### [NEW] [ProtocolVerifier.py](backend/ai_engines/protocol.py)
*   **Purpose**: Cross-references claims against a "Hard Protocol" checklist.
*   **Violations Flagged**: 
    - "Arrest via Video Call" = **CRITICAL VIOLATION**
    - "Payment via UPI to avoid jail" = **CRITICAL VIOLATION**
    - "Warrant served on WhatsApp" = **CRITICAL VIOLATION**

#### [MODIFY] [VisionForensics.py](backend/ai_engines/vision.py)
*   **Primary**: **Warrant Forensic Analysis**. Check for logo distortions, invalid IPC sections, and template deviations.
*   **Secondary**: **Currency PoC**. Basic classifier trained on public Kaggle datasets for ₹500 notes.

---

### Phase 2: Action & Scalability

#### [NEW] [InterventionService.py](backend/services/intervention.py)
*   **The "Kill Switch"**: Simulates API calls to `UPI_HOLD`, `BANK_LOCK`, or `TELECOM_FLAG`.
*   **Logic**: If Risk Score > 85% AND "Financial Extraction" stage is detected, fire intervention.

---

### Phase 3: The Demo & Evaluation

#### [NEW] [EvaluationFramework.py](backend/tests/eval_metrics.py)
*   **The Rigor**: A small dataset of ~50 processed transcripts (Scambaiting YouTube samples + Real news clips).
*   **Output**: Generates a **Precision/Recall matrix** to be shown on the final slide.

#### [NEW] [LawEnforcementDashboard.tsx](frontend/src/components/Dashboard.tsx)
*   **The Narrative**: High-fidelity dashboard showing:
    - Live Transcription Streaming.
    - **Risk Meter** climbing in real-time as the "Scam Arc" progresses.
    - **Intervention Triggered** toast notification.

## Scalability Roadmap (The "Pro" Slide)
1.  **Async Processing**: Redis/Celery for high-volume call analysis.
2.  **Vector DB**: Pinecone for the Legal RAG corpus (Indian Penal Code + Police Guidelines).
3.  **Edge Implementation**: Lightweight CV models for on-device currency scanning.

## Verification Plan

### Automated Evaluation
- Run `eval_metrics.py` to ensure Precision > 90% on the curated test set.

### Manual Demo Walkthrough
1.  **Human Stakes**: Open with 5 seconds of a real crying victim's call.
2.  **Live Action**: Feed the scam transcript into the app.
3.  **The Win**: Show the risk meter hitting Red and the "Intervention: Bank Hold Initialized" message appearing.
