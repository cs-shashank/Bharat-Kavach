# Bharat Kavach: AI-Powered Digital Public Safety

Bharat Kavach is a forensic AI platform designed to protect Indian citizens from "Digital Arrest" scams, cyber-fraud, and counterfeit currency. 

## Project Objective
The platform uses **Behavioral Intelligence** to track the escalation arc of a scam and triggers **proactive interventions** (like simulated bank holds) before financial loss occurs.

## Tech Stack
- **Backend**: FastAPI, LangChain, Google Gemini 1.5 Flash.
- **AI Engines**: 
  - `BehavioralClassifier.py`: Stage-based scam detection.
  - `ProtocolVerifier.py`: Red-flag logic for legal protocol violations.
  - `InterventionService.py`: Mock webhooks for banking/telecom actions.
- **Frontend**: React (TBD).
- **Vision**: OpenCV / SIFT (TBD).

## Current Status (Day 1 of 10)
- [x] Backend structure initialized.
- [x] Core Behavioral Classifier implemented.
- [x] Protocol Violation logic implemented.
- [x] Initial commit pushed to GitHub.

## Next Steps for the Team
1. **Legal RAG**: Indexing IPC/BNS documents to cross-reference legal claims.
2. **Vision Forensics**: Implementing warrant and currency verification.
3. **Frontend**: Building the Law Enforcement Dashboard.

Refer to the [docs/implementation_plan.md](docs/implementation_plan.md) and [docs/task.md](docs/task.md) for the detailed 10-day roadmap.
