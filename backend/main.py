import os
from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket, WebSocketDisconnect
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
from ai_engines.intervention import InterventionService
from database import get_db, CaseReport, ForensicDocument
from sqlalchemy.orm import Session
from fastapi import Depends

# Load environment variables
load_dotenv()

app = FastAPI(title="Bharat Kavach API", version="1.0.0")

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
        for connection in self.active_connections:
            await connection.send_text(message)

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

@app.get("/")
def read_root():
    return {"message": "Bharat Kavach Backend is Online"}

@app.post("/analyze")
async def analyze_call(request: TranscriptRequest, db: Session = Depends(get_db)):
    # ... logic for analysis ...
    analysis = classifier.analyze_transcript(request.transcript) if classifier else None
    legal_findings = legal_rag.verify_legal_claims(request.transcript) if legal_rag else []
    
    # Save to Database (The "Production" Step)
    new_case = CaseReport(
        user_id=request.user_id,
        transcript=request.transcript,
        risk_score=analysis.confidence * 100 if analysis else 90.0,
        stage=analysis.current_stage if analysis else "Detected",
        verdict="SCAM_DETECTED",
        legal_citations=[f.dict() for f in legal_findings],
        interventions=[]
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)

    # Broadcast to live dashboard
    await manager.broadcast(json.dumps({
        "type": "FORENSIC_UPDATE",
        "data": {
            "id": new_case.id,
            "score": new_case.risk_score, 
            "stage": new_case.stage,
            "findings": new_case.legal_citations
        }
    }))
    
    return {"id": new_case.id, "status": "SAVED"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
