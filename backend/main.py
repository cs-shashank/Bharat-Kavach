import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# Import our AI engines
from ai_engines.behavioral import BehavioralClassifier, AnalysisResult
from ai_engines.protocol import ProtocolVerifier
from services.intervention import InterventionService

# Load environment variables
load_dotenv()

app = FastAPI(title="Bharat Kavach API", version="1.0.0")

# Initialize Classifier (Requires API Key)
# We handle the missing key case gracefully for the user
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
classifier = None
if GOOGLE_API_KEY:
    classifier = BehavioralClassifier(api_key=GOOGLE_API_KEY)

class TranscriptRequest(BaseModel):
    transcript: str
    user_id: Optional[str] = "DEMO_USER_001"

@app.get("/")
def read_root():
    return {"message": "Bharat Kavach Backend is Online"}

@app.post("/analyze")
async def analyze_call(request: TranscriptRequest):
    if not classifier:
        # For the hackathon, we can return a mock result if API key is missing
        # But we prompt the user to add it.
        return {
            "error": "GOOGLE_API_KEY not found in .env",
            "instruction": "Please add your Gemini API key to the .env file to see AI-powered analysis."
        }
    
    # 1. Behavioral Classification (LLM)
    analysis = classifier.analyze_transcript(request.transcript)
    
    # 2. Protocol Check (Heuristic)
    verifier = ProtocolVerifier()
    violations = verifier.check_violations(request.transcript)
    
    # 3. Decision Logic & Intervention
    intervention_status = None
    if analysis.intervention_required or len(violations) > 0:
        intervention_status = InterventionService.trigger_kill_switch(
            scam_type=analysis.current_stage,
            victim_id=request.user_id
        )
    
    return {
        "analysis": analysis.dict(),
        "protocol_violations": violations,
        "intervention": intervention_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
