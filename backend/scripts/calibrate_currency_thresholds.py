"""
calibrate_currency_thresholds.py
=================================
Run this against your genuine/counterfeit folders to find empirical
threshold values for CurrencyVerifier.

Usage:
  cd backend
  python scripts/calibrate_currency_thresholds.py

Output: min/max/mean of edge_density and sharpness_variance per class.
Use the output to pick thresholds that sit between the two distributions.
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engines.currency import CurrencyVerifier
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "test_assets" / "currency"
verifier = CurrencyVerifier()


def collect_features(folder: Path):
    feats = []
    if not folder.exists():
        print(f"  WARNING: folder not found: {folder}")
        return feats
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith((".jpg", ".png")):
            continue
        img_bytes = (folder / fname).read_bytes()
        result = verifier.verify_note(img_bytes)
        if "signals" in result:
            feats.append({
                "file": fname,
                **result["signals"]
            })
    return feats


def summarize(name, feats):
    if not feats:
        print(f"\n{name}: NO DATA")
        return
    ed = [f["edge_density"] for f in feats]
    sv = [f["sharpness_variance"] for f in feats]
    cs = [f["channel_separation"] for f in feats]
    print(f"\n{name} (n={len(feats)}):")
    print(f"  edge_density     min={min(ed):.4f}  max={max(ed):.4f}  mean={sum(ed)/len(ed):.4f}")
    print(f"  sharpness_var    min={min(sv):.2f}  max={max(sv):.2f}  mean={sum(sv)/len(sv):.2f}")
    print(f"  channel_sep      min={min(cs):.2f}  max={max(cs):.2f}  mean={sum(cs)/len(cs):.2f}")
    # Show bottom 5 edge_density for debugging
    sorted_by_edge = sorted(feats, key=lambda x: x["edge_density"])
    print(f"  Lowest edge_density files: {[f['file'] for f in sorted_by_edge[:3]]}")


print("=" * 60)
print("CURRENCY VERIFIER CALIBRATION")
print("=" * 60)

genuine_feats     = collect_features(BASE / "genuine")
counterfeit_feats = collect_features(BASE / "counterfeit")

summarize("GENUINE",     genuine_feats)
summarize("COUNTERFEIT", counterfeit_feats)

# Suggest thresholds
if genuine_feats and counterfeit_feats:
    g_ed_mean = sum(f["edge_density"] for f in genuine_feats) / len(genuine_feats)
    c_ed_mean = sum(f["edge_density"] for f in counterfeit_feats) / len(counterfeit_feats)
    g_sv_mean = sum(f["sharpness_variance"] for f in genuine_feats) / len(genuine_feats)
    c_sv_mean = sum(f["sharpness_variance"] for f in counterfeit_feats) / len(counterfeit_feats)

    ed_mid = round((g_ed_mean + c_ed_mean) / 2, 4)
    sv_mid = round((g_sv_mean + c_sv_mean) / 2, 2)

    print(f"\n{'=' * 60}")
    print("SUGGESTED THRESHOLDS (midpoint between means):")
    print(f"  edge_density_threshold = {ed_mid}")
    print(f"  sharpness_threshold    = {sv_mid}")
    print()
    if abs(g_ed_mean - c_ed_mean) < 0.02 and abs(g_sv_mean - c_sv_mean) < 50:
        print("⚠️  WARNING: Genuine and counterfeit distributions overlap heavily.")
        print("   Simple OpenCV heuristics cannot reliably separate this dataset.")
        print("   Honest finding for pitch deck: 'Classical CV features show limited")
        print("   separability on this sample; production requires a trained CNN.'")
    else:
        print("✅ Distributions appear separable. Update CurrencyVerifier.__init__ with:")
        print(f"   edge_density_threshold={ed_mid}, sharpness_threshold={sv_mid}")
    print("=" * 60)
