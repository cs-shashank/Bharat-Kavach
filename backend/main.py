import os
import logging
import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
import json
from typing import List, Optional, Dict
from dotenv import load_dotenv

# Import our AI engines
from ai_engines.behavioral import BehavioralClassifier, AnalysisResult
from ai_engines.protocol import ProtocolVerifier
from ai_engines.legal_rag import LegalRAG
from ai_engines.vision import VisionForensics
from ai_engines.currency import CurrencyVerifier
from services.intervention import InterventionService
from services.evidence_exporter import EvidenceExporter, EvidenceBundle
from services.fraud_network import FraudNetworkAnalyzer
from database import get_db, CaseReport, ForensicDocument
from sqlalchemy.orm import Session
from fastapi import Depends

# Load environment variables
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bharat Kavach API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("bharat_kavach")

# Evidence exporter (Phase 1)
exporter = EvidenceExporter()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.active_connections.remove(connection)

manager = ConnectionManager()

# Initialize Classifier (Requires API Key)
# We handle the missing key case gracefully for the user
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
classifier = None
if GOOGLE_API_KEY:
    legal_rag = LegalRAG(api_key=GOOGLE_API_KEY)
    vision_engine = VisionForensics(api_key=GOOGLE_API_KEY, legal_rag_engine=legal_rag)
    currency_engine = CurrencyVerifier()
    classifier = BehavioralClassifier(api_key=GOOGLE_API_KEY)
    MOCK_MODE = False
else:
    classifier = None
    legal_rag = None
    vision_engine = None
    currency_engine = None
    MOCK_MODE = True

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class TranscriptRequest(BaseModel):
    transcript: str
    user_id: Optional[str] = "DEMO_USER_001"
    city: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Bharat Kavach Backend is Online"}

@app.post("/analyze")
async def analyze_call(request: TranscriptRequest, db: Session = Depends(get_db)):
    # Run AI analysis (or use mock values when no API key is present)
    analysis = classifier.analyze_transcript(request.transcript) if classifier else None
    legal_findings = legal_rag.verify_legal_claims(request.transcript) if legal_rag else []

    risk_score = analysis.confidence * 100 if analysis else 90.0
    stage = analysis.current_stage if analysis else "Financial Demand / UPI Request"

    # --- Kill-switch logic (Req 5) ---
    KILL_SWITCH_STAGE = "Financial Demand / UPI Request"
    intervention_triggered = False
    intervention_result = None
    intervention_error = None

    # Build the case record first so we can attach interventions to it
    new_case = CaseReport(
        user_id=request.user_id,
        transcript=request.transcript,
        risk_score=risk_score,
        stage=stage,
        verdict="SCAM_DETECTED",
        legal_citations=[f.dict() for f in legal_findings],
        interventions=[],
        city=request.city,
    )

    if risk_score > 85 and stage == KILL_SWITCH_STAGE:
        try:
            result = InterventionService.trigger_kill_switch(
                scam_type="Digital Arrest",
                victim_id=request.user_id,
            )
            intervention_triggered = True
            intervention_result = {
                "actions_taken": result["actions_taken"],
                "incident_id": result["incident_id"],
            }
            new_case.interventions = result["actions_taken"]

            # Broadcast KILL_SWITCH_TRIGGERED to all connected Dashboard clients
            await manager.broadcast(json.dumps({
                "type": "KILL_SWITCH_TRIGGERED",
                "data": {
                    "actions_taken": result["actions_taken"],
                    "incident_id": result["incident_id"],
                    "risk_score": risk_score,
                    "stage": stage,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                },
            }))
        except Exception as e:
            logger.exception("Intervention failed")
            intervention_triggered = False
            intervention_error = f"Intervention failed: {str(e)}"
            new_case.interventions = []

    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Broadcast FORENSIC_UPDATE regardless of intervention outcome
    await manager.broadcast(json.dumps({
        "type": "FORENSIC_UPDATE",
        "data": {
            "id": new_case.id,
            "score": new_case.risk_score,
            "stage": new_case.stage,
            "findings": new_case.legal_citations,
        },
    }))

    # Build response — always include core fields
    response: Dict = {
        "id": new_case.id,
        "status": "SAVED",
        "risk_score": risk_score,
        "stage": stage,
        "legal_citations": new_case.legal_citations,
        "intervention_triggered": intervention_triggered,
    }

    # Conditionally attach intervention_result or intervention_error
    if intervention_triggered and intervention_result is not None:
        response["intervention_result"] = intervention_result
    elif intervention_error is not None:
        response["intervention_error"] = intervention_error

    return response

@app.post("/analyze-currency")
async def analyze_currency(file: UploadFile = File(...)):
    if MOCK_MODE:
        return {
            "status": "ANALYZED",
            "note_type": "500_INR",
            "signals": {"thread_detected": True, "is_suspicious": False},
            "disclaimer": "DEMO MOCK"
        }
        
    if not currency_engine:
        return {"error": "Currency Engine not initialized."}
        
    contents = await file.read()
    results = currency_engine.verify_note(contents)
    return results

@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    if MOCK_MODE:
        return {
            "is_warrant": True,
            "verdict": "Likely Fake",
            "confidence_score": 0.88,
            "forensic_signals": {
                "geometric_sanity": 0.4,
                "semantic_format": 0.3,
                "legal_consistency": 0.2
            },
            "explanation": "DEMO MODE: Geometric anomalies in court seal detected."
        }
    if not vision_engine:
        return {"error": "Vision Engine not initialized. Add GOOGLE_API_KEY."}
    
    contents = await file.read()
    results = vision_engine.analyze_document(contents)
    
    return results.dict()

@app.get("/cases")
async def get_cases(db: Session = Depends(get_db)):
    cases = db.query(CaseReport).order_by(CaseReport.timestamp.desc()).all()
    return cases

@app.get("/metrics")
async def get_metrics():
    if MOCK_MODE:
        return {
            "total_samples": 40,
            "precision": 0.93,
            "recall": 0.91,
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

# ---------------------------------------------------------------------------
# Phase 1 — Evidence export endpoints
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/evidence")
async def get_case_evidence(case_id: int, db: Session = Depends(get_db)):
    """
    Return the full EvidenceBundle JSON for a case, plus a pdf_url download link.
    Idempotent: serves the cached bundle if it already exists on disk.
    """
    case = db.query(CaseReport).filter(CaseReport.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        bundle = exporter.get_or_create_bundle(case)
    except Exception as exc:
        logger.exception("Evidence bundle generation failed for case %s", case_id)
        raise HTTPException(status_code=500, detail=f"Evidence generation failed: {str(exc)}")

    bundle_dict = bundle.model_dump()
    bundle_dict["pdf_url"] = f"/cases/{case_id}/evidence/download"
    return bundle_dict


@app.get("/cases/{case_id}/evidence/download")
async def download_case_evidence_pdf(case_id: int, db: Session = Depends(get_db)):
    """
    Stream the PDF summary for a case as a downloadable attachment.
    """
    case = db.query(CaseReport).filter(CaseReport.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Resolve bundle_id — try to read from cached JSON first
    bundle_id = getattr(case, "bundle_id", None)
    if not bundle_id:
        # Try to get_or_create to populate bundle_id
        try:
            bundle = exporter.get_or_create_bundle(case)
            bundle_id = bundle.bundle_id
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Evidence generation failed: {str(exc)}")

    pdf_path = exporter.get_pdf_path(bundle_id)
    if not pdf_path.exists():
        # Attempt to generate
        try:
            bundle = exporter.get_or_create_bundle(case)
            pdf_path = exporter.get_pdf_path(bundle.bundle_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(exc)}")

    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF not yet generated for this case")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
        headers={"Content-Disposition": f"attachment; filename={pdf_path.name}"},
    )


# ---------------------------------------------------------------------------
# Fraud Network Graph Intelligence — PS Requirement 3
# ---------------------------------------------------------------------------

_fraud_analyzer = FraudNetworkAnalyzer()

@app.get("/fraud-network")
async def get_fraud_network(db: Session = Depends(get_db)):
    """
    Build and return a NetworkX fraud graph from all high-risk cases.
    Returns nodes, edges, centrality metrics, hub detection, and
    court-admissible evidence export.
    """
    cases = db.query(CaseReport).filter(CaseReport.risk_score > 60).order_by(
        CaseReport.timestamp.desc()
    ).limit(100).all()

    if not cases:
        return {
            "nodes": [], "edges": [],
            "hub_count": 0, "victim_count": 0,
            "total_nodes": 0, "total_edges": 0,
            "cluster_count": 0,
            "analytic_insight": "No high-risk cases available for network analysis.",
            "exportable_evidence": {}
        }

    result = _fraud_analyzer.build_graph(cases)
    return {
        "nodes": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "label": n.label,
                "case_ids": n.case_ids,
                "degree_centrality": n.degree_centrality,
                "betweenness_centrality": n.betweenness_centrality,
                "is_hub": n.is_hub,
            }
            for n in result.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target,
             "edge_type": e.edge_type, "weight": e.weight}
            for e in result.edges
        ],
        "hub_count": result.hub_count,
        "victim_count": result.victim_count,
        "total_nodes": result.total_nodes,
        "total_edges": result.total_edges,
        "cluster_count": result.cluster_count,
        "analytic_insight": result.analytic_insight,
        "exportable_evidence": result.exportable_evidence,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
