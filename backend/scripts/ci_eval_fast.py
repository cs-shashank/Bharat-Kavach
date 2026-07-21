#!/usr/bin/env python
"""
ci_eval_fast.py — Fast CI gate covering all four components.

- BehavioralClassifier + LegalRAG: 20 India-specific + 10 Jim Browning transcripts
- VisionForensics: 10 authentic + 10 forged document images
- CurrencyVerifier: all genuine + counterfeit currency images (196 genuine, 25 counterfeit)

Completes in ~12 minutes on free tier.
Exit codes: 0=PASS, 1=FAIL, 2=CONFIG ERROR
"""

import os, sys, json, time
from pathlib import Path
from datetime import datetime, timezone

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

from services.eval_pipeline import (
    EvaluationPipeline, EvalResultStore,
    MANIFEST_PATH, THRESHOLDS, MIN_SAMPLES_FOR_GATE,
    ComponentMetrics, EvalRunResult, TEST_ASSETS_DIR,
)
from scripts.ci_eval import check_thresholds, print_pass_summary
import subprocess


def get_git_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5,
                           cwd=str(_BACKEND_DIR))
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def fast_eval(manifest: dict, api_key: str) -> EvalRunResult:
    """Run eval on targeted samples for all four components."""
    from ai_engines.behavioral import BehavioralClassifier
    from ai_engines.legal_rag import LegalRAG
    from ai_engines.protocol import ProtocolVerifier
    from ai_engines.currency import CurrencyVerifier

    print("[fast_eval] Initialising AI engines...")
    behavioral = BehavioralClassifier(api_key=api_key)
    legal_rag   = LegalRAG(api_key=api_key)
    protocol    = ProtocolVerifier()
    currency    = CurrencyVerifier()
    print(f"[fast_eval] BehavioralClassifier model: {behavioral.model}")

    # ── Transcript samples ────────────────────────────────────────────
    india_ids = {f"tr_scam_{i:03d}" for i in range(1, 11)} | \
                {f"tr_legit_{i:03d}" for i in range(1, 11)}
    jim_ids   = {f"tr_scam_{i:03d}" for i in range(11, 21)}
    transcript_ids = india_ids | jim_ids

    transcript_samples = [s for s in manifest["samples"]
                          if s["sample_type"] == "transcript"
                          and s["sample_id"] in transcript_ids]

    # ── Document image samples (first 10 of each class) ───────────────
    doc_samples = [s for s in manifest["samples"]
                   if s["sample_type"] == "document_image"]
    doc_auth   = [s for s in doc_samples if s["ground_truth"] == "authentic"][:10]
    doc_forged = [s for s in doc_samples if s["ground_truth"] == "forged"][:10]
    doc_eval   = doc_auth + doc_forged

    # ── Currency image samples (first 10 of each class) ───────────────
    cur_samples = [s for s in manifest["samples"]
                   if s["sample_type"] == "currency_image"]
    cur_genuine     = [s for s in cur_samples if s["ground_truth"] == "genuine"]
    cur_counterfeit = [s for s in cur_samples if s["ground_truth"] == "counterfeit"]
    cur_eval        = cur_genuine + cur_counterfeit

    scam_t  = sum(1 for s in transcript_samples if s["ground_truth"] == "scam")
    legit_t = sum(1 for s in transcript_samples if s["ground_truth"] == "legit")
    print(f"[fast_eval] Transcripts: {len(transcript_samples)} ({scam_t} scam, {legit_t} legit)")
    print(f"[fast_eval] Documents:   {len(doc_eval)} ({len(doc_forged)} forged, {len(doc_auth)} authentic)")
    print(f"[fast_eval] Currency:    {len(cur_eval)} ({len(cur_counterfeit)} counterfeit, {len(cur_genuine)} genuine)")

    bc_pairs, lr_pairs, vf_pairs, cv_pairs = [], [], [], []
    errors = []

    # ── Transcript eval ───────────────────────────────────────────────
    print("\n[fast_eval] --- TRANSCRIPT EVAL ---")
    for idx, sample in enumerate(transcript_samples, 1):
        sid = sample["sample_id"]
        gt  = sample["ground_truth"]
        txt = sample.get("transcript", "")
        print(f"[fast_eval] {idx}/{len(transcript_samples)}: {sid} ({gt})", flush=True)

        # BehavioralClassifier
        try:
            time.sleep(5)
            result = behavioral.analyze_transcript(txt)
            predicted = "scam" if result.confidence * 100 > 85 else "legit"
            bc_pairs.append({"ground_truth": gt, "predicted": predicted})
            print(f"  BC: {predicted} (conf={result.confidence:.2f})")
        except Exception as e:
            errors.append({"sample_id": sid, "component": "BehavioralClassifier", "error": str(e)[:80]})
            print(f"  BC ERROR: {str(e)[:80]}")

        # LegalRAG
        try:
            time.sleep(5)
            findings  = legal_rag.verify_legal_claims(txt)
            violations = protocol.check_violations(txt)
            myths     = any(f.verdict == "confirmed_false" for f in findings)
            predicted_lr = "scam" if (myths or violations) else "legit"
            lr_pairs.append({"ground_truth": gt, "predicted": predicted_lr})
            print(f"  LR: {predicted_lr} (myths={myths})")
        except Exception as e:
            errors.append({"sample_id": sid, "component": "LegalRAG", "error": str(e)[:80]})
            print(f"  LR ERROR: {str(e)[:80]}")

    # ── Document image eval (VisionForensics — OpenCV only, no API) ───
    print("\n[fast_eval] --- DOCUMENT EVAL (VisionForensics) ---")
    try:
        from ai_engines.vision import VisionForensics
        vision = VisionForensics(api_key=api_key, legal_rag_engine=legal_rag)

        for idx, sample in enumerate(doc_eval, 1):
            sid = sample["sample_id"]
            gt  = sample["ground_truth"]
            # Resolve file path
            rel_path = sample.get("file_path", "")
            # Remove leading subdirectory prefix if present
            if rel_path.startswith("documents/"):
                img_path = TEST_ASSETS_DIR / rel_path
            else:
                img_path = TEST_ASSETS_DIR / "documents" / rel_path

            print(f"[fast_eval] doc {idx}/{len(doc_eval)}: {sid} ({gt})", flush=True)

            if not img_path.exists():
                print(f"  VF: SKIP (file not found: {img_path})")
                errors.append({"sample_id": sid, "component": "VisionForensics",
                               "error": f"file not found: {img_path}"})
                continue
            try:
                img_bytes = img_path.read_bytes()
                time.sleep(5)  # rate limit for Gemini vision calls
                result = vision.analyze_document(img_bytes)
                
                # Use VisionForensics verdict directly — it uses Gemini + OpenCV ensemble
                verdict_lower = result.verdict.lower()
                confidence = result.confidence_score
                
                # Forged if verdict says fake/suspicious AND confidence > 0.6
                if ("fake" in verdict_lower or "suspicious" in verdict_lower) and confidence > 0.6:
                    predicted = "forged"
                elif "authentic" in verdict_lower and confidence > 0.6:
                    predicted = "authentic"
                else:
                    # Use seal confidence as tiebreaker
                    predicted = "forged" if result.seal_confidence < 0.3 else "authentic"
                vf_pairs.append({"ground_truth": gt, "predicted": predicted})
                print(f"  VF: {predicted} (verdict={result.verdict[:40]})")
            except Exception as e:
                errors.append({"sample_id": sid, "component": "VisionForensics", "error": str(e)[:80]})
                print(f"  VF ERROR: {str(e)[:80]}")
    except Exception as e:
        print(f"[fast_eval] VisionForensics init failed: {e}")

    # ── Currency image eval (CurrencyVerifier — OpenCV only, no API) ──
    print("\n[fast_eval] --- CURRENCY EVAL (CurrencyVerifier) ---")
    for idx, sample in enumerate(cur_eval, 1):
        sid = sample["sample_id"]
        gt  = sample["ground_truth"]
        rel_path = sample.get("file_path", "")
        if rel_path.startswith("currency/"):
            img_path = TEST_ASSETS_DIR / rel_path
        else:
            img_path = TEST_ASSETS_DIR / "currency" / rel_path

        print(f"[fast_eval] cur {idx}/{len(cur_eval)}: {sid} ({gt})", flush=True)

        if not img_path.exists():
            print(f"  CV: SKIP (file not found: {img_path})")
            errors.append({"sample_id": sid, "component": "CurrencyVerifier",
                           "error": f"file not found: {img_path}"})
            continue
        try:
            img_bytes = img_path.read_bytes()
            result = currency.verify_note(img_bytes)
            is_suspicious = result.get("signals", {}).get("is_suspicious", False)
            predicted = "counterfeit" if is_suspicious else "genuine"
            cv_pairs.append({"ground_truth": gt, "predicted": predicted})
            print(f"  CV: {predicted} (suspicious={is_suspicious})")
        except Exception as e:
            errors.append({"sample_id": sid, "component": "CurrencyVerifier", "error": str(e)[:80]})
            print(f"  CV ERROR: {str(e)[:80]}")

    # ── Compute metrics ───────────────────────────────────────────────
    pipeline = EvaluationPipeline(api_key=api_key)

    def mk_metrics(name, pairs):
        if not pairs:
            return ComponentMetrics(name, 0, 0.0, 0.0, 0.0, 0.0)
        m = pipeline.compute_metrics(pairs)
        m.component = name
        return m

    git_sha = get_git_sha()
    run_at  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id  = f"{git_sha}_{run_at}"

    per_component = {
        "BehavioralClassifier": mk_metrics("BehavioralClassifier", bc_pairs),
        "LegalRAG":             mk_metrics("LegalRAG",             lr_pairs),
        "VisionForensics":      mk_metrics("VisionForensics",      vf_pairs),
        "CurrencyVerifier":     mk_metrics("CurrencyVerifier",     cv_pairs),
    }

    run_result = EvalRunResult(
        run_id=run_id,
        manifest_version=manifest.get("manifest_version", 3),
        git_commit_sha=git_sha,
        run_at=run_at,
        per_component=per_component,
        eval_errors=errors,
    )

    pipeline._print_summary(run_result)
    EvalResultStore().save(run_result)
    return run_result


def main():
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        print("[ci_eval_fast] ERROR: GOOGLE_API_KEY not set.", file=sys.stderr)
        sys.exit(2)

    if not MANIFEST_PATH.exists():
        print(f"[ci_eval_fast] ERROR: Manifest not found.", file=sys.stderr)
        sys.exit(2)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(f"[ci_eval_fast] Manifest v{manifest.get('manifest_version')}: "
          f"{len(manifest.get('samples', []))} total samples")
    print(f"[ci_eval_fast] Estimated time: ~12 minutes\n")

    run_result = fast_eval(manifest, api_key)
    failures = check_thresholds(run_result)

    if failures:
        print("\n" + "=" * 70)
        print("  BHARAT KAVACH CI GATE (FAST) — FAIL")
        print("=" * 70)
        for msg in failures:
            print(msg)
        print("=" * 70)
        sys.exit(1)
    else:
        print_pass_summary(run_result)
        sys.exit(0)


if __name__ == "__main__":
    main()
