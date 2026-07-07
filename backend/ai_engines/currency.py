import cv2
import numpy as np
from typing import Dict, List
import io
from PIL import Image

class CurrencyVerifier:
    """
    Forensic verification module for Indian Currency (₹500 Focus).
    Uses Region of Interest (ROI) analysis for security features.
    """
    
    def __init__(self):
        # Normalized coordinates for ₹500 security features (percentage of width/height)
        self.ROIS_500 = {
            "security_thread": {"x": (0.6, 0.65), "y": (0.0, 1.0)},
            "watermark_gandhi": {"x": (0.75, 0.95), "y": (0.2, 0.8)},
            "bleeding_lines": {"x": (0.0, 0.05), "y": (0.3, 0.7)},
        }

    def _get_roi(self, img: np.ndarray, roi_name: str):
        h, w = img.shape[:2]
        coords = self.ROIS_500[roi_name]
        x_start, x_end = int(coords["x"][0] * w), int(coords["x"][1] * w)
        y_start, y_end = int(coords["y"][0] * h), int(coords["y"][1] * h)
        return img[y_start:y_end, x_start:x_end]

    def verify_note(self, image_bytes: bytes) -> Dict:
        """
        Main entry point for currency forensic audit.
        """
        # Convert bytes to OpenCV image
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image format"}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Security Thread Continuity Check
        thread_roi = self._get_roi(gray, "security_thread")
        _, binary_thread = cv2.threshold(thread_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thread_density = np.sum(binary_thread == 0) / binary_thread.size
        
        # 2. Watermark Histogram Analysis (Checking for 'washed' appearance)
        watermark_roi = self._get_roi(gray, "watermark_gandhi")
        std_dev = np.std(watermark_roi)
        
        # Forensic Verdict Logic
        features = {
            "thread_detected": thread_density > 0.05,
            "thread_density_score": round(float(thread_density), 3),
            "watermark_complexity_score": round(float(std_dev), 2),
            "is_suspicious": False
        }
        
        # Detection of 'Photocopy' attempts (Flat histogram in watermark area)
        if std_dev < 15.0 or thread_density < 0.02:
            features["is_suspicious"] = True
            features["reason"] = "Low complexity in security regions (Possible scan/print)"
            
        return {
            "status": "ANALYZED",
            "note_type": "500_INR_NEW",
            "signals": features,
            "disclaimer": "POC Mode: Forensic estimate only."
        }

if __name__ == "__main__":
    print("CurrencyVerifier module loaded.")
