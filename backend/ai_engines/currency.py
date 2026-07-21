import cv2
import numpy as np
from typing import Dict


class CurrencyVerifier:
    """
    Forensic verification module for Indian Currency — denomination-agnostic.

    Uses edge density + local sharpness variance (Laplacian) across the
    whole note, since fixed per-denomination ROIs don't generalize across
    ₹10/₹20/₹50/₹100/₹200/₹500/₹2000 notes.

    Thresholds are calibrated empirically via scripts/calibrate_currency_thresholds.py
    against the actual genuine/counterfeit image folders.
    """

    def __init__(self,
                 edge_density_threshold: float = 0.1034,
                 sharpness_threshold: float = 1883.12):
        # Starting defaults — override after running calibrate_currency_thresholds.py
        self.edge_density_threshold = edge_density_threshold
        self.sharpness_threshold = sharpness_threshold

    def _compute_features(self, img: np.ndarray) -> Dict:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (600, 300))  # normalize scale across denominations

        # Edge density — genuine notes have fine, dense microprinting
        # Counterfeit prints often blur/smear fine lines → lower edge density
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size

        # Local sharpness (Laplacian variance) — genuine intaglio printing
        # has crisp raised-ink edges; counterfeit offset/inkjet prints are softer
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Color channel separation — genuine notes use specific ink formulations
        # Poor-quality counterfeits often have muddier, less-separated channels
        b, g, r = cv2.split(cv2.resize(img, (600, 300)))
        channel_std = float(np.std([np.std(b), np.std(g), np.std(r)]))

        return {
            "edge_density": round(float(edge_density), 4),
            "sharpness_variance": round(float(laplacian_var), 2),
            "channel_separation": round(channel_std, 2),
        }

    def verify_note(self, image_bytes: bytes) -> Dict:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image format"}

        features = self._compute_features(img)

        # Ensemble: flag suspicious only when BOTH signals are weak
        # (avoids false positives from low-quality genuine note photos)
        is_suspicious = (
            features["edge_density"] < self.edge_density_threshold
            and features["sharpness_variance"] < self.sharpness_threshold
        )

        return {
            "status": "ANALYZED",
            "note_type": "INR_MULTI_DENOMINATION_POC",
            "signals": {**features, "is_suspicious": is_suspicious},
            "disclaimer": (
                "POC Mode: Denomination-agnostic forensic heuristic. "
                "Not certified — production requires a trained CNN classifier."
            ),
        }


if __name__ == "__main__":
    print("CurrencyVerifier module loaded.")
