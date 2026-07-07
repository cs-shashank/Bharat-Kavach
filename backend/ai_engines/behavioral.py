import os
import json
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class ScamStage(Enum):
    NORMAL = "Normal Conversation"
    AUTHORITY = "Authority Impersonation (CBI/Police/NCB)"
    ISOLATION = "Digital Confinement / Isolation (Don't tell family)"
    EVIDENCE = "Fabricated Evidence / Illegal Acts"
    URGENCY = "Urgency / Fear Injection"
    DEMAND = "Financial Demand / UPI Request"

class AnalysisResult(BaseModel):
    current_stage: str
    confidence: float
    reasoning: str
    red_flags: List[str]
    intervention_required: bool

class BehavioralClassifier:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def analyze_transcript(self, transcript: str) -> AnalysisResult:
        prompt = f"""
        You are a Forensic Cybercrime Analyst specializing in Indian "Digital Arrest" scams.
        Analyze the following transcript segment and classify it based on the Scam Escalation Arc.

        SCAM STAGES:
        1. Normal Conversation: Casual talk, no threats.
        2. Authority Impersonation: Caller claims to be from CBI, Police, Custom, RBI, or NCB.
        3. Digital Confinement / Isolation: Caller tells victim to stay on video call, not tell family, or stay in a room.
        4. Fabricated Evidence: Claims of illegal parcels, drugs, Aadhaar misuse, or money laundering.
        5. Urgency / Fear Injection: Threatening immediate arrest, social shame, or jail time.
        6. Financial Demand: Asking for a 'security deposit', 'verification fee', or UPI transfer.

        TRANSCRIPT: {transcript}

        Return a JSON response matching this structure:
        {{
          "current_stage": "string",
          "confidence": float,
          "reasoning": "string",
          "red_flags": ["string"],
          "intervention_required": boolean
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            return AnalysisResult(**data)
        except Exception as e:
            print(f"Behavioral Analysis failed: {e}")
            return AnalysisResult(
                current_stage="Unknown",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                red_flags=[],
                intervention_required=False
                )

if __name__ == "__main__":
    print("BehavioralClassifier initialized.")
