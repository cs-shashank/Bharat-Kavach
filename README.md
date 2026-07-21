# 🛡️ Bharat Kavach — AI-Powered Digital Public Safety Platform

> **Protecting Indian citizens from Digital Arrest scams, cyber-fraud, counterfeit currency, and document forgery with State-of-the-Art Forensics.**

[![Tests](https://img.shields.io/badge/Backend%20Tests-29%20Passing-brightgreen?style=for-the-badge&logo=pytest)](#-testing-ecosystem)
[![Frontend](https://img.shields.io/badge/Frontend%20Tests-39%20Passing-brightgreen?style=for-the-badge&logo=vitest)](#-testing-ecosystem)
[![Languages](https://img.shields.io/badge/Languages-12%20Regional-blue?style=for-the-badge)](#-citizen-multilingual-support)

---

## 🌟 Vision & Key Capabilities

Bharat Kavach ("India's Shield") is a comprehensive, multi-engine digital public safety platform tailored for law enforcement officers, forensic investigators, and Indian citizens:

*   🚨 **Digital Arrest Detection**: Automatically flags coercive call flows using a `BehavioralClassifier` that matches live transcripts to a verified 6-stage escalation arc.
*   ⚖️ **Legal Claim Verification**: Debunks authoritative-sounding legal myths (like fake "UPI freezes" and "illegal parcels") by verifying claims against a trusted **BNS/BNSS** legal database.
*   🔍 **Document Forgery Analysis**: Analyzes summons, warrants, and letters using OpenCV structural forensics combined with Gemini Vision models.
*   💵 **Counterfeit Currency Verification**: Detects fake Indian currency notes via denomination-agnostic edge density and Laplacian sharpness distributions.
*   🕸️ **Fraud Network Graphs**: Maps and clusters scam networks, tracking linked phone numbers, money mules, and central perpetrator nodes via NetworkX.
*   📦 **Auditable Evidence Export**: Exports tamper-evident, SHA-256 integrity-hashed ZIP/JSON evidence packages containing timeline records and interactive PDF summaries.
*   🗣️ **Regional Language Alerts**: Supports citizen engagement and chat interactions in **12 distinct Indian languages**.

---

## 📊 CI Quality Gate Metrics (Run: `4cb992e`)

The platform enforces a strict Continuous Integration quality gate on our representative v3 manifest dataset (290 total samples) to ensure zero false positives (`FPR == 0.00`) on critical scam detection engines:

| 🧩 Component | 📦 Sample Size | 🎯 Precision | 🔄 Recall | ⚡ F1 Score | 📉 False Positive Rate | 🚦 Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **BehavioralClassifier** | 30 | **1.000** | 0.700 | 0.824 | **0.000** | ✅ **PASS** |
| **LegalRAG** | 30 | **1.000** | 0.650 | 0.788 | **0.000** | ✅ **PASS** |
| **VisionForensics** | 20 | **0.818** | 0.900 | 0.857 | **0.200** | ✅ **PASS** |
| **CurrencyVerifier** | 50 | **0.867** | 0.520 | 0.650 | **0.080** | ✅ **PASS** |

> [!NOTE]
> All core engines are calibrated against real-world distributions. The CurrencyVerifier thresholds are optimized at `edge_density = 0.1034` and `sharpness = 1883.12` based on empirical dataset separation.

---

## 🛠️ Core Technology Stack

| Layer | ⚙️ Technologies & Libraries |
| :--- | :--- |
| **Backend API** | FastAPI (Python) |
| **AI Foundations** | Google Gemini 3.1 Flash Lite API via official `google-genai` SDK |
| **Legal Grounding** | Custom BNS/BNSS database (12 verified provisions cross-checked with Gazette) |
| **Vision Forensics** | OpenCV (Structural seal/signature analysis) + Gemini Vision models |
| **Currency Forensics** | OpenCV Laplacian variance + Edge density extractors |
| **Graph Intelligence** | NetworkX (Betweenness centrality, Degree centrality, Louvain clustering) |
| **Evidence Building** | ReportLab PDF + JSON serialization with SHA-256 integrity signatures |
| **Frontend Board** | React (Vite) + TailwindCSS + Recharts + Framer Motion (Transitions) |
| **Quality Testing** | Hypothesis (Property-based tests) + Vitest & fast-check (Components) |
| **Storage layer** | SQLite DB accessed via SQLAlchemy ORM |

---

## 📂 Project Directory Structure

```
bharat-kavach/
├── backend/
│   ├── ai_engines/
│   │   ├── behavioral.py      # 6-stage scam classifier (Gemini)
│   │   ├── legal_rag.py       # BNS/BNSS legal claim verifier
│   │   ├── vision.py          # Document forgery detector (OpenCV + Gemini)
│   │   ├── currency.py        # Counterfeit currency detector (OpenCV)
│   │   └── protocol.py        # Protocol violation checker
│   ├── services/
│   │   ├── evidence_exporter.py   # SHA-256 bundle + PDF export
│   │   ├── eval_pipeline.py       # Evaluation pipeline + metrics
│   │   └── fraud_network.py       # NetworkX graph intelligence
│   ├── scripts/
│   │   ├── ci_eval_fast.py        # Fast CI gate (all 4 components)
│   │   └── calibrate_currency_thresholds.py
│   ├── data/
│   │   ├── legal_kb.json          # 12 BNS/BNSS verified entries
│   │   ├── eval_manifest.json     # 290 labeled samples (v3)
│   │   └── test_assets/           # Currency + document images
│   └── main.py                    # FastAPI app (12 endpoints)
└── frontend/
    └── src/components/
        ├── dashboard/             # Law enforcement dashboard
        └── forensics/             # Risk meter, fraud network, etc.
```

---

## 🚀 Quick Start Guide

### 💻 Setting up the Backend
```bash
cd backend
pip install -r requirements.txt

# Create your .env file inside backend/ and configure api keys:
# GOOGLE_API_KEY=your_google_gemini_api_key_here

python main.py
# API server running at http://localhost:8000
```

### 🎨 Setting up the Frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard interface running at http://localhost:5173
```

---

## 🔌 Key API Endpoints

| Method | Route | 📋 Description |
| :---: | :--- | :--- |
| `POST` | `/analyze` | Analyze calls/messages/transcripts for scams and BNS violations |
| `POST` | `/analyze-document` | Upload official warrants/summons/letters to inspect for forgery |
| `POST` | `/analyze-currency` | Upload Indian bank note photos to verify authenticity signals |
| `GET` | `/fraud-network` | Retrieve NetworkX-computed fraud ring graph data |
| `GET` | `/cases/{id}/evidence` | Fetch the tamper-evident SHA-256 JSON evidence bundle |
| `GET` | `/cases/{id}/evidence/download` | Download the court-admissible PDF Summary Report |
| `GET` | `/cases` | Query case records list & history |
| `GET` | `/metrics` | Query live engine metrics and evaluation outcomes |

---

## 🧪 Testing Ecosystem

### 🐍 Backend Property-Based Testing
Execute the SQLite, PDF, and pipeline tests generated via **Hypothesis** (run from project root):
```bash
python -m pytest backend/tests/ -v
```

### ⚡ Frontend Component Testing
Execute the React + Vitest + fast-check properties test suite:
```bash
cd frontend
npm run test
```

### 🚦 CI Evaluation Runner
Simulate the continuous integration evaluation pipeline run:
```bash
cd backend

# Linux / macOS
GOOGLE_API_KEY=<your_key> python scripts/ci_eval_fast.py

# Windows (PowerShell)
$env:GOOGLE_API_KEY="<your_key>"; python scripts/ci_eval_fast.py

# Windows (CMD)
set GOOGLE_API_KEY=<your_key> && python scripts/ci_eval_fast.py
```

---

## 🗣️ Citizen Multilingual Support

The Citizen App contains localization data supporting speech, alerts, and instructions in **12 different Indian regional languages**:
$$\text{English } \cdot \text{ हिन्दी } \cdot \text{ தமிழ் } \cdot \text{ తెలుగు } \cdot \text{ বাংলা } \cdot \text{ मराठी } \cdot \text{ ગુજરાતી } \cdot \text{ ಕನ್ನಡ } \cdot \text{ മലയാളം } \cdot \text{ ਪੰਜਾਬੀ } \cdot \text{ ଓଡ଼ିଆ } \cdot \text{ اردو }$$

---

## 📑 Evidence Auditability & Custody

Every case processed by Bharat Kavach produces a digital chain-of-custody log:
*   🔑 **Integrity Signing**: Computes a SHA-256 hash over all verdict data fields. Any manual db alteration invalidates the signature.
*   📦 **Traceability**: Chronologically captures timestamp, runtime engine versions, and status logs inside the metadata registry.
*   💾 **Resiliency**: Built-in dual-path writing failsafe. If JSON IO fails, it rolls back and writes timestamped errors to a secondary logging system.

---

## ⚖️ Legal Disclaimer

> [!IMPORTANT]
> Bharat Kavach is an automated forensic software assistance tool intended to flag security threats. It is not an official government platform, certified testing agency, or legal advisory. All forensic indicators must be manually verified by a licensed investigator before being filed as formal legal evidence.

---

## 🗃️ Datasets & Calibration Sources

*   **Scam Transcripts**: Adapted and paraphrased from public MHA I4C advisories, NDTV Cyber Crime reports, and scambaiter video script logs.
*   **Legal RAG Grounding**: Matches and validates claims strictly against the official **Gazette of India (BNS, 2023 / BNSS, 2023)** database.
*   **Document Images**: Sourced from case history disclosures, authentic gazette warrants, and synthetic templates.
*   **Currency Dataset**: Sourced from Kaggle rupee counterfeit identification datasets across multiple denominations.
