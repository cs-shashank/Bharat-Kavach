"""
VisionForensics — Gemini-powered document forensics.

Uses the new google.genai SDK with structured output and inline image bytes.
Ensemble pipeline: OpenCV deterministic signals + Gemini Vision LLM + LegalRAG.
"""
import cv2
import numpy as np
import os
import io
import json
import time
import re
from typing import Dict, Optional
from pydantic import BaseModel
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

_MODEL_PREFERENCE = [
    "gemini-3.1-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-flash-lite-latest",
]


class VisionAnalysisResult(BaseModel):
    is_warrant: bool
    verdict: str
    confidence_score: float
    seal_confidence: float
    forensic_signals: Dict[str, float]
    explanation: str
    disclaimer: str = "Automated forensic estimate — not a certified document examination"


class VisionForensics:
    def __init__(self, api_key: str, legal_rag_engine=None):
        self.client = genai.Client(api_key=api_key)
        self.model = self._pick_model()
        self.legal_rag = legal_rag_engine
        self.templates_path = os.path.join(_BACKEND_DIR, "assets", "templates")
        os.makedirs(self.templates_path, exist_ok=True)

    def _pick_model(self) -> str:
        for model in _MODEL_PREFERENCE:
            try:
                self.client.models.generate_content(model=model, contents="ping")
                return model
            except Exception as e:
                if "404" in str(e) or "429" in str(e):
                    continue
        return "gemini-flash-lite-latest"

    def _generate(self, contents, response_schema=None, retries: int = 3) -> str:
        config = {}
        if response_schema:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = response_schema

        for attempt in range(retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(**config) if config else None,
                )
                return response.text.strip()
            except Exception as e:
                err = str(e)
                if "429" in err and attempt < retries - 1:
                    m = re.search(r"seconds:\s*(\d+)", err)
                    delay = int(m.group(1)) + 2 if m else 60
                    print(f"[VisionForensics] Rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise

    def _preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Deskew, denoise, and CLAHE-enhance for best OCR/CV accuracy."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        coords = np.column_stack(np.where(denoised > 0))
        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        lab = cv2.cvtColor(rotated, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(l)
        return cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2BGR)

    def _geometric_analysis(self, img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
        score = 0.5 + (0.2 if lines is not None and len(lines) > 5 else 0.0)
        return min(score, 1.0)

    def _verify_seal_integrity(self, image: np.ndarray) -> float:
        template_path = os.path.join(self.templates_path, "official_seal.png")
        if not os.path.exists(template_path):
            return 0.5
        template = cv2.imread(template_path, 0)
        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(image, None)
        if des1 is None or des2 is None:
            return 0.0
        matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des1, des2)
        return min(1.0, len(matches) / 50.0)

    def analyze_document(self, image_bytes: bytes) -> VisionAnalysisResult:
        """Ensemble: OpenCV geometry + Gemini Vision + LegalRAG → fused verdict."""
        processed_img_cv = self._preprocess_image(image_bytes)
        _, buffer = cv2.imencode(".jpg", processed_img_cv)
        processed_bytes = buffer.tobytes()

        geometric_score = self._geometric_analysis(processed_img_cv)
        seal_score = self._verify_seal_integrity(processed_img_cv)
        combined_cv_score = (geometric_score * 0.4) + (seal_score * 0.6)

        # Gemini Vision — structured output
        vision_schema = {
            "type": "object",
            "properties": {
                "vision_llm_assessment": {"type": "string"},
                "ocr_text": {"type": "string"},
                "is_anomalous": {"type": "boolean"},
                "confidence": {"type": "number"},
            },
            "required": ["vision_llm_assessment", "ocr_text", "is_anomalous", "confidence"],
        }

        vision_prompt = """Perform a high-rigor forensic audit on this legal document image.
1. Semantic Assessment: Does the formatting, tone, and signature block match official Indian government conventions?
2. Visual Anomalies: Are there artifacts suggesting digital overlays, font mismatches, or generated signatures?
3. OCR Extraction: Extract the core legal claim/charges.
Return strictly valid JSON with these fields: vision_llm_assessment, ocr_text, is_anomalous (bool), confidence (float 0-1)."""

        try:
            image_part = types.Part.from_bytes(data=processed_bytes, mime_type="image/jpeg")
            text_part = vision_prompt
            raw = self._generate([text_part, image_part], response_schema=vision_schema)
            if "```" in raw:
                raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
        except Exception:
            data = {"vision_llm_assessment": "AI Error", "ocr_text": "", "is_anomalous": False, "confidence": 0.5}

        # LegalRAG cross-reference
        legal_status = "Not checked"
        legal_score = 0.5
        if self.legal_rag and data.get("ocr_text"):
            try:
                legal_findings = self.legal_rag.verify_legal_claims(data["ocr_text"])
                myths = [f.explanation for f in legal_findings if f.verdict == "confirmed_false"]
                legal_status = " | ".join(myths) if myths else "Plausible legal procedure"
                legal_score = 0.0 if myths else 1.0
            except Exception:
                pass

        # Decision fusion
        overall_confidence = (legal_score * 0.5) + (data["confidence"] * 0.3) + (combined_cv_score * 0.2)
        final_verdict = "Likely Fake" if data["is_anomalous"] else "Appears Authentic"
        if seal_score < 0.2:
            final_verdict = "Highly Suspicious — Seal Tampering Detected"
            overall_confidence = max(0.9, overall_confidence)

        return VisionAnalysisResult(
            is_warrant=not data["is_anomalous"],
            verdict=final_verdict,
            confidence_score=round(overall_confidence, 2),
            seal_confidence=round(seal_score, 2),
            forensic_signals={
                "geometric_sanity": round(geometric_score, 2),
                "seal_integrity": round(seal_score, 2),
                "semantic_validity": round(float(data["confidence"]), 2),
                "legal_grounding": round(legal_score, 2),
            },
            explanation=f"Vision: {data['vision_llm_assessment']}. Legal: {legal_status}.",
        )
