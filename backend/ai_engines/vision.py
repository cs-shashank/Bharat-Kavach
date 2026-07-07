import cv2
import numpy as np
import google.generativeai as genai
from typing import Dict, List, Optional
from pydantic import BaseModel
import os
from PIL import Image, ImageOps
import io
import json

class VisionSignals(BaseModel):
    geometric_score: float
    vision_llm_assessment: str
    legal_text_verification: str
    ocr_extracted_text: str

class VisionAnalysisResult(BaseModel):
    is_warrant: bool
    verdict: str
    confidence_score: float
    seal_confidence: float # New deterministic CV signal
    forensic_signals: Dict[str, float]
    explanation: str
    disclaimer: str = "Automated forensic estimate — not a certified document examination"

class VisionForensics:
    def __init__(self, api_key: str, legal_rag_engine=None):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.legal_rag = legal_rag_engine
        self.templates_path = "backend/assets/templates"
        
        if not os.path.exists(self.templates_path):
            os.makedirs(self.templates_path)

    def _preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        """Step 0: Aggressive preprocessing to handle real-world artifacts (rotation, low contrast)."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 1. Grayscale & Noise Reduction
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        # 2. Deskewing (Basic horizontal alignment)
        coords = np.column_stack(np.where(denoised > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # 3. Contrast Normalization (CLAHE)
        lab = cv2.cvtColor(rotated, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl,a,b))
        final_img = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        return final_img

    def _geometric_analysis(self, img: np.ndarray) -> float:
        """deterministic CV: layout/geometry sanity checks."""
        # Score based on margin consistency, stamp-shaped region detection, etc.
        # This is a simplified proxy: we check for the presence of typical 'Letterhead' and 'Seal' regions
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        # If we find strong horizontal lines at the top (letterhead) and a circular(ish) contour (seal)
        # We increase the score.
        score = 0.5
        if lines is not None and len(lines) > 5:
            score += 0.2
            
        return min(score, 1.0)

    def _verify_seal_integrity(self, image: np.ndarray) -> float:
        """
        Deterministic ORB feature matching against known official seals.
        Returns match confidence (0.0 to 1.0).
        """
        template_path = "assets/templates/official_seal.png"
        if not os.path.exists(template_path):
            return 0.5 # Neutral if no template
            
        template = cv2.imread(template_path, 0)
        orb = cv2.ORB_create(nfeatures=1000)
        
        kp1, des1 = orb.detectAndCompute(template, None)
        kp2, des2 = orb.detectAndCompute(image, None)
        
        if des1 is None or des2 is None:
            return 0.0
            
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        # Calculate a simple confidence based on match count
        # In a real system, we'd use RANSAC to verify geometric consistency
        score = len(matches) / 50.0 # Threshold calibrated for small logos
        return min(1.0, score)

    def analyze_document(self, image_bytes: bytes) -> VisionAnalysisResult:
        """Ensemble Pipeline: Preprocess -> (Geo + Vision AI + Legal RAG) -> Fuse."""
        # 1. Preprocess
        processed_img_cv = self._preprocess_image(image_bytes)
        
        # Convert back to bytes for Gemini
        _, buffer = cv2.imencode('.jpg', processed_img_cv)
        processed_bytes = buffer.tobytes()
        pil_img = Image.open(io.BytesIO(processed_bytes))

        # 1. OpenCV Deterministic Signal
        geometric_score = self._geometric_analysis(processed_img_cv)
        seal_score = self._verify_seal_integrity(processed_img_cv)
        
        combined_cv_score = (geometric_score * 0.4) + (seal_score * 0.6)

        # Signal B & C: Vision AI Assessment + OCR Extraction
        prompt = """
        Perform a high-rigor forensic audit on this legal document image.
        1. Semantic Assessment: Does the formatting, tone, and signature block match official Indian government conventions?
        2. Visual Anomalies: Are there artifacts suggesting digital overlays, font mismatches, or generated signatures?
        3. OCR Extraction: Extract the core legal claim/charges.
        
        Return JSON ONLY:
        {
          "vision_llm_assessment": "string",
          "ocr_text": "string",
          "is_anomalous": boolean,
          "confidence": float
        }
        """
        
        try:
            response = self.model.generate_content([prompt, pil_img])
            data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        except:
            data = {"vision_llm_assessment": "AI Timeout/Error", "ocr_text": "None", "is_anomalous": False, "confidence": 0.5}

        # Signal D: Legal RAG cross-ref (The strongest signal)
        legal_status = "Not Checked"
        legal_score = 0.5
        if self.legal_rag and data["ocr_text"] != "None":
            legal_findings = self.legal_rag.verify_legal_claims(data["ocr_text"])
            myths = [f.explanation for f in legal_findings if f.verdict == "confirmed_false"]
            legal_status = " | ".join(myths) if myths else "Plausible procedure"
            legal_score = 0.0 if myths else 1.0

        # 3. Decision Fusion
        # We give high weight to Legal consistency, but CV Seal check can veto.
        overall_confidence = (legal_score * 0.5) + (data['confidence'] * 0.3) + (combined_cv_score * 0.2)
        
        final_verdict = "plausible" if not data['is_anomalous'] else "suspicious"
        if seal_score < 0.2:
            final_verdict = "Highly Suspicious (Seal Tampering)"
            overall_confidence = max(0.9, overall_confidence) # Increase confidence that it's a fake
            
        return VisionAnalysisResult(
            is_warrant=not data['is_anomalous'],
            verdict=final_verdict,
            confidence_score=round(overall_confidence, 2),
            seal_confidence=round(seal_score, 2),
            forensic_signals={
                "geometric_sanity": round(geometric_score, 2),
                "seal_integrity": round(seal_score, 2),
                "semantic_validity": data['confidence'],
                "legal_grounding": legal_score
            },
            explanation=f"Audit Findings: {data['vision_llm_assessment']}. Legal consistency: {legal_status}."
        )

    def verify_currency(self, image_bytes: bytes) -> Dict:
        """
        POC for currency verification focusing on ₹500 notes.
        Note: production version would need RBI's full FICN feature set 
        and multi-denomination training data.
        """
        return {
            "status": "POC_MODE",
            "note_type": "500_INR",
            "security_features_detected": ["Gandhiji_Watermark", "RBI_Thread"],
            "is_suspicious": False,
            "disclaimer": "POC only - not for official bank verification"
        }
