"""
BehavioralClassifier — Gemini-powered scam stage detection.

Uses the new google.genai SDK with structured output (response_schema)
to guarantee well-formed JSON and eliminate fragile string parsing.
"""
import os
import json
import time
import re
from typing import List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load .env from the backend directory regardless of cwd
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

# Model preference list — first available is used
_MODEL_PREFERENCE = [
    "gemini-3.1-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-lite-latest",
]


class AnalysisResult(BaseModel):
    current_stage: str
    confidence: float
    reasoning: str
    red_flags: List[str]
    intervention_required: bool


class BehavioralClassifier:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model = self._pick_model()

    def _pick_model(self) -> str:
        """Return the first model in the preference list that responds."""
        for model in _MODEL_PREFERENCE:
            try:
                self.client.models.generate_content(
                    model=model,
                    contents="ping",
                )
                return model
            except Exception as e:
                if "404" in str(e):
                    continue  # model not available
                if "429" in str(e):
                    continue  # quota exhausted on this model, try next
        # Fall back to lite model which is most likely available
        return "gemini-flash-lite-latest"

    def _generate(self, prompt: str, response_schema=None, retries: int = 3) -> str:
        """Call Gemini with automatic retry on rate-limit."""
        config = {}
        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        for attempt in range(retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config) if config else None,
                )
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err and attempt < retries - 1:
                    m = re.search(r"seconds:\s*(\d+)", err)
                    delay = int(m.group(1)) + 2 if m else 5
                    delay = min(delay, 10)  # cap at 10s — rate limiter handles pacing
                    print(f"[BehavioralClassifier] Rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise

    def analyze_transcript(self, transcript: str) -> AnalysisResult:
        """
        Classify the transcript against the 6-stage Digital Arrest scam arc.
        Returns a structured AnalysisResult with confidence score.
        """
        prompt = f"""
You are a Forensic Cybercrime Analyst specialising in Indian "Digital Arrest" scams.
Analyse the transcript and classify it against the Scam Escalation Arc.

SCAM STAGES:
1. Normal Conversation       — Casual talk, no threats.
2. Authority Impersonation   — Caller claims to be CBI / Police / Customs / RBI / NCB.
3. Digital Confinement       — Victim told to stay on video call, not tell family, stay alone.
4. Fabricated Evidence       — Claims of illegal parcels, drugs, Aadhaar misuse, money laundering.
5. Urgency / Fear Injection  — Immediate arrest threats, social shame, jail time.
6. Financial Demand / UPI Request — 'Security deposit', 'verification fee', UPI / RTGS transfer.

TRANSCRIPT:
{transcript}

Return strictly valid JSON with these exact fields:
- current_stage (string): one of the six stage names above
- confidence (float 0.0–1.0): your certainty
- reasoning (string): 1-2 sentence explanation
- red_flags (array of strings): specific phrases that triggered classification
- intervention_required (boolean): true if stage is Financial Demand or Urgency
"""
        # Response schema for structured output — guarantees valid JSON
        response_schema = {
            "type": "object",
            "properties": {
                "current_stage": {"type": "string"},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "red_flags": {"type": "array", "items": {"type": "string"}},
                "intervention_required": {"type": "boolean"},
            },
            "required": ["current_stage", "confidence", "reasoning", "red_flags", "intervention_required"],
        }

        try:
            text = self._generate(prompt, response_schema=response_schema)
            # Strip markdown fences if model adds them despite mime type
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip() if "```json" in text else text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)
            # Clamp confidence to [0, 1]
            data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
            return AnalysisResult(**data)
        except Exception as e:
            print(f"[BehavioralClassifier] Analysis failed: {e}")
            return AnalysisResult(
                current_stage="Unknown",
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                red_flags=[],
                intervention_required=False,
            )


if __name__ == "__main__":
    print("BehavioralClassifier ready.")
