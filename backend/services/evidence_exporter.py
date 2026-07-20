"""
evidence_exporter.py — Bharat Kavach Phase 1

Assembles AI engine outputs into a cryptographically-signed EvidenceBundle,
serialises it to JSON, and generates a human-readable PDF summary via reportlab.

This module never calls any AI engine directly. It only receives already-computed
output objects and serialises them. It also never imports from main.py.
"""

import uuid
import json
import hashlib
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Directory / path constants
# ---------------------------------------------------------------------------

EXPORTS_DIR = Path("backend/data/evidence_exports")
FAILURE_LOG = Path("backend/logs/evidence_export_failures.log")
SCHEMA_PATH = Path("backend/schemas/evidence_bundle.schema.json")

COMPONENT_NAMES = [
    "BehavioralClassifier",
    "LegalRAG",
    "VisionForensics",
    "CurrencyVerifier",
]

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class EvidenceExportError(Exception):
    """Base exception for all evidence export failures."""


class HashComputationError(EvidenceExportError):
    """Raised when SHA-256 hash computation fails."""


class JsonWriteError(EvidenceExportError):
    """Raised when writing the JSON evidence bundle to disk fails."""


class PdfGenerationError(EvidenceExportError):
    """Raised when PDF generation via reportlab fails."""


class FallbackWriteError(EvidenceExportError):
    """Raised when the failure-log fallback write also fails."""


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ChainOfCustodyEntry(BaseModel):
    """A single step in the chain of custody for an evidence bundle."""

    step: int
    component: str
    artifact_type: Literal["transcript", "document_image", "currency_image"]
    action: str
    timestamp: str  # ISO 8601


class ComponentVerdict(BaseModel):
    """The verdict produced by one AI component for a case."""

    verdict: str
    confidence: Optional[float] = None  # None for not_applicable; constrained [0.0, 1.0] when not None
    details: Optional[dict] = None      # None for not_applicable


class EvidenceBundle(BaseModel):
    """
    The complete, cryptographically-signed evidence package for a single case.

    ``sha256_hash`` is populated by ``EvidenceExporter.compute_hash()`` after
    all other fields have been set. It covers the canonical serialisation of
    every other top-level field (see ``compute_hash`` for the exact algorithm).
    """

    bundle_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analyzed_at: str
    case_id: int
    sha256_hash: str = ""  # populated by compute_hash()
    model_registry: dict[str, str]
    chain_of_custody: list[ChainOfCustodyEntry]
    component_verdicts: dict[str, ComponentVerdict]


# ---------------------------------------------------------------------------
# EvidenceExporter
# ---------------------------------------------------------------------------


class EvidenceExporter:
    """
    Wraps AI engine outputs into an ``EvidenceBundle``, computes an integrity
    hash, and writes the bundle to disk as JSON and PDF.

    The exporter is deliberately stateless with respect to AI engines — it
    receives already-computed result objects and never calls any engine itself.
    """

    EXPORTS_DIR = EXPORTS_DIR
    FAILURE_LOG = FAILURE_LOG
    SCHEMA_PATH = SCHEMA_PATH

    # ------------------------------------------------------------------
    # Bundle construction
    # ------------------------------------------------------------------

    def build_bundle(
        self,
        case_id: int,
        transcript: str,
        behavioral_result=None,
        legal_findings=None,
        vision_result=None,
        currency_result=None,
        model_registry: dict[str, str] = None,
    ) -> EvidenceBundle:
        """
        Assemble all component outputs into a complete, hashed EvidenceBundle.

        Parameters
        ----------
        case_id:
            Integer foreign key referencing the CaseReport row.
        transcript:
            The raw transcript text that was analysed.
        behavioral_result:
            Output from BehavioralClassifier, or ``None`` if not invoked.
        legal_findings:
            Output from LegalRAG (list of LegalClaim), or ``None`` if not invoked.
        vision_result:
            Output from VisionForensics, or ``None`` if not invoked.
        currency_result:
            Output from CurrencyVerifier (dict), or ``None`` if not invoked.
        model_registry:
            Mapping of component name → model ID string.

        Returns
        -------
        EvidenceBundle
            A fully assembled bundle with ``sha256_hash`` already set.
        """
        # 1. Generate bundle_id and analyzed_at timestamp
        bundle_id = str(uuid.uuid4())
        analyzed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # 2. Resolve model_registry — use provided or default to "unknown" for all components
        if model_registry is None:
            model_registry = {
                "BehavioralClassifier": "unknown",
                "LegalRAG": "unknown",
                "VisionForensics": "unknown",
                "CurrencyVerifier": "unknown",
            }

        # 3. Map each component result to a ComponentVerdict
        # --- BehavioralClassifier ---
        if behavioral_result is None:
            behavioral_verdict = ComponentVerdict(verdict="not_applicable", confidence=None, details=None)
        else:
            behavioral_verdict = ComponentVerdict(
                verdict=behavioral_result.current_stage,
                confidence=behavioral_result.confidence,
                details={
                    "current_stage": behavioral_result.current_stage,
                    "reasoning": behavioral_result.reasoning,
                    "red_flags": behavioral_result.red_flags,
                    "intervention_required": behavioral_result.intervention_required,
                },
            )

        # --- LegalRAG ---
        if legal_findings is None:
            legal_verdict = ComponentVerdict(verdict="not_applicable", confidence=None, details=None)
        else:
            findings_list = legal_findings  # list of LegalClaim
            myths_count = sum(1 for f in findings_list if f.verdict == "confirmed_false")
            has_confirmed_false = any(f.verdict == "confirmed_false" for f in findings_list)
            legal_verdict = ComponentVerdict(
                verdict="confirmed_false" if has_confirmed_false else "unverifiable",
                confidence=1.0 if findings_list else None,
                details={
                    "claims_verified": len(findings_list),
                    "myths_detected": myths_count,
                    "findings": [f.dict() for f in findings_list],
                },
            )

        # --- VisionForensics ---
        if vision_result is None:
            vision_verdict = ComponentVerdict(verdict="not_applicable", confidence=None, details=None)
        else:
            vision_verdict = ComponentVerdict(
                verdict=vision_result.verdict,
                confidence=vision_result.confidence_score,
                details=vision_result.dict(),
            )

        # --- CurrencyVerifier ---
        if currency_result is None:
            currency_verdict = ComponentVerdict(verdict="not_applicable", confidence=None, details=None)
        else:
            is_suspicious = currency_result.get("signals", {}).get("is_suspicious", False)
            currency_verdict = ComponentVerdict(
                verdict="suspicious" if is_suspicious else "genuine",
                confidence=None,
                details=currency_result,
            )

        component_verdicts = {
            "BehavioralClassifier": behavioral_verdict,
            "LegalRAG": legal_verdict,
            "VisionForensics": vision_verdict,
            "CurrencyVerifier": currency_verdict,
        }

        # 4. Build chain_of_custody — one entry per non-None component, in order
        component_inputs = [
            ("BehavioralClassifier", behavioral_result, "transcript"),
            ("LegalRAG", legal_findings, "transcript"),
            ("VisionForensics", vision_result, "document_image"),
            ("CurrencyVerifier", currency_result, "currency_image"),
        ]

        chain_of_custody = []
        step = 1
        entry_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        for component_name, result, artifact_type in component_inputs:
            if result is not None:
                chain_of_custody.append(
                    ChainOfCustodyEntry(
                        step=step,
                        component=component_name,
                        artifact_type=artifact_type,
                        action=f"{component_name} analysis completed",
                        timestamp=entry_timestamp,
                    )
                )
                step += 1

        # 5. Construct the EvidenceBundle
        bundle = EvidenceBundle(
            bundle_id=bundle_id,
            analyzed_at=analyzed_at,
            case_id=case_id,
            sha256_hash="",
            model_registry=model_registry,
            chain_of_custody=chain_of_custody,
            component_verdicts=component_verdicts,
        )

        # 6. Compute and set the SHA-256 hash (compute_hash implemented in task 3.2)
        bundle.sha256_hash = self.compute_hash(bundle)

        # 7. Return the bundle
        return bundle

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def compute_hash(self, bundle: EvidenceBundle) -> str:
        """
        Return the SHA-256 hex digest of the bundle's canonical serialisation.

        The hash covers every top-level field **except** ``sha256_hash`` itself.
        Canonical form: ``json.dumps(payload, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True)`` → UTF-8 encoded → SHA-256.

        Raises
        ------
        HashComputationError
            If serialisation or hashing fails for any reason.
        """
        try:
            payload = {
                "bundle_id": bundle.bundle_id,
                "analyzed_at": bundle.analyzed_at,
                "case_id": bundle.case_id,
                "model_registry": bundle.model_registry,
                "chain_of_custody": [entry.model_dump() for entry in bundle.chain_of_custody],
                "component_verdicts": {
                    k: v.model_dump() for k, v in bundle.component_verdicts.items()
                },
            }
            serialised = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
            encoded = serialised.encode("utf-8")
            return hashlib.sha256(encoded).hexdigest()
        except Exception as e:
            raise HashComputationError(str(e))

    def verify_hash(self, bundle: EvidenceBundle) -> bool:
        """
        Return ``True`` if ``bundle.sha256_hash`` matches the recomputed hash.

        Recomputes the hash via ``compute_hash()`` and compares it to the
        stored value. Returns ``False`` on any mismatch (including if the
        stored hash is empty).

        Returns
        -------
        bool
            ``True`` if the bundle has not been tampered with, ``False`` otherwise.
        """
        if bundle.sha256_hash == "":
            return False
        try:
            recomputed = self.compute_hash(bundle)
            return recomputed == bundle.sha256_hash
        except HashComputationError:
            return False

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, bundle: EvidenceBundle) -> Path:
        """
        Serialise the bundle to ``EXPORTS_DIR/BK-{bundle_id}.evidence.json``.

        Dual-path failure handling
        --------------------------
        * **Component serialisation error** — if any ``component_verdicts``
          entry raises a serialisation exception, append a
          ``chain_of_custody`` entry with
          ``action = "serialisation_error: {ExceptionType}"`` and continue
          writing the partial export (other components intact). The partial
          file is still written and its path returned.
        * **Filesystem write failure** — attempt a plain-text append to
          ``FAILURE_LOG`` in the format
          ``"FAILURE|{bundle_id}|{timestamp}|{exception_type}|{exception_msg}\\n"``.
          If the fallback also fails, log to stderr only. Then raise
          ``JsonWriteError``.

        Returns
        -------
        Path
            Absolute path to the written ``.evidence.json`` file.

        Raises
        ------
        JsonWriteError
            If the primary filesystem write fails (after attempting the
            fallback log).
        """
        import sys

        # Build the payload dict, serialising each component verdict individually
        # so that a single component's failure does not abort the entire export.
        safe_verdicts: dict = {}
        for component_name, verdict in bundle.component_verdicts.items():
            try:
                safe_verdicts[component_name] = verdict.model_dump()
            except Exception as exc:
                # Record serialisation failure in chain_of_custody
                error_action = f"serialisation_error: {type(exc).__name__}"
                bundle.chain_of_custody.append(
                    ChainOfCustodyEntry(
                        step=len(bundle.chain_of_custody) + 1,
                        component=component_name,
                        artifact_type="transcript",  # best-effort default
                        action=error_action,
                        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    )
                )
                # Use a sentinel placeholder so the key is still present
                safe_verdicts[component_name] = {
                    "verdict": "serialisation_error",
                    "confidence": None,
                    "details": {"error": str(exc)},
                }

        payload = {
            "bundle_id": bundle.bundle_id,
            "analyzed_at": bundle.analyzed_at,
            "case_id": bundle.case_id,
            "sha256_hash": bundle.sha256_hash,
            "model_registry": bundle.model_registry,
            "chain_of_custody": [entry.model_dump() for entry in bundle.chain_of_custody],
            "component_verdicts": safe_verdicts,
        }

        # Ensure the exports directory exists
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

        output_path = self.EXPORTS_DIR / f"BK-{bundle.bundle_id}.evidence.json"

        try:
            json_str = json.dumps(payload, indent=2, ensure_ascii=True, default=str)
            output_path.write_text(json_str, encoding="utf-8")
            return output_path.resolve()
        except Exception as primary_exc:
            # Primary write failed — attempt plain-text fallback log
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            failure_line = (
                f"FAILURE|{bundle.bundle_id}|{timestamp_str}"
                f"|{type(primary_exc).__name__}|{str(primary_exc)}\n"
            )
            try:
                self.FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
                with open(self.FAILURE_LOG, "a", encoding="utf-8") as flog:
                    flog.write(failure_line)
            except Exception as fallback_exc:
                # Both paths failed — last resort is stderr
                print(
                    f"[EvidenceExporter] CRITICAL: primary and fallback both failed. "
                    f"bundle_id={bundle.bundle_id} primary={primary_exc!r} fallback={fallback_exc!r}",
                    file=sys.stderr,
                )
            raise JsonWriteError(str(primary_exc)) from primary_exc

    def export_pdf(self, bundle: EvidenceBundle) -> Path:
        """
        Generate ``EXPORTS_DIR/BK-{bundle_id}.summary.pdf`` using reportlab.

        PDF sections (in order)
        -----------------------
        1. Header — title, bundle_id, case_id
        2. Analysis Timestamp — human-readable ``analyzed_at``
        3. Component Verdicts Table — 4 rows; ``not_applicable`` rows show
           ``—`` in Verdict and Confidence columns
        4. Chain of Custody Timeline — one line per step with timestamp
        5. SHA-256 Integrity Footer — hash in monospace font
        6. Disclaimer — fixed statutory text

        Returns
        -------
        Path
            Absolute path to the written ``.summary.pdf`` file.

        Raises
        ------
        PdfGenerationError
            If reportlab fails to generate or write the PDF.
        """
        try:
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            )
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT

            self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            pdf_path = self.EXPORTS_DIR / f"BK-{bundle.bundle_id}.summary.pdf"

            doc = SimpleDocTemplate(
                str(pdf_path),
                pagesize=A4,
                leftMargin=20 * mm,
                rightMargin=20 * mm,
                topMargin=20 * mm,
                bottomMargin=20 * mm,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "Title", parent=styles["Heading1"],
                fontSize=14, spaceAfter=6, alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                "Heading", parent=styles["Heading2"],
                fontSize=11, spaceAfter=4
            )
            body_style = styles["BodyText"]
            mono_style = ParagraphStyle(
                "Mono", parent=styles["BodyText"],
                fontName="Courier", fontSize=8, wordWrap="CJK"
            )
            disclaimer_style = ParagraphStyle(
                "Disclaimer", parent=styles["Italic"],
                fontSize=8, textColor=colors.grey
            )

            story = []

            # 1 — Header
            story.append(Paragraph("BHARAT KAVACH — FORENSIC EVIDENCE SUMMARY", title_style))
            story.append(Paragraph(f"Bundle ID: {bundle.bundle_id}", body_style))
            story.append(Paragraph(f"Case ID: {bundle.case_id}", body_style))
            story.append(Spacer(1, 6 * mm))

            # 2 — Analysis Timestamp
            story.append(Paragraph("Analysis Timestamp", heading_style))
            story.append(Paragraph(bundle.analyzed_at, body_style))
            story.append(Spacer(1, 4 * mm))

            # 3 — Component Verdicts Table
            story.append(Paragraph("Component Verdicts", heading_style))
            table_data = [["Component", "Verdict", "Confidence"]]
            for name in COMPONENT_NAMES:
                cv = bundle.component_verdicts.get(name)
                if cv is None or cv.verdict == "not_applicable":
                    table_data.append([name, "\u2014", "\u2014"])
                else:
                    conf_str = f"{cv.confidence:.2f}" if cv.confidence is not None else "\u2014"
                    table_data.append([name, cv.verdict, conf_str])

            verdict_table = Table(
                table_data,
                colWidths=[55 * mm, 80 * mm, 30 * mm],
                hAlign="LEFT",
            )
            verdict_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",   (0, 0), (-1, -1), 9),
                ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(verdict_table)
            story.append(Spacer(1, 6 * mm))

            # 4 — Chain of Custody Timeline
            story.append(Paragraph("Chain of Custody", heading_style))
            if bundle.chain_of_custody:
                for entry in bundle.chain_of_custody:
                    story.append(Paragraph(
                        f"Step {entry.step} [{entry.timestamp}] "
                        f"{entry.component}: {entry.action}",
                        body_style,
                    ))
            else:
                story.append(Paragraph("No components invoked.", body_style))
            story.append(Spacer(1, 6 * mm))

            # 5 — SHA-256 Integrity Footer
            story.append(Paragraph("SHA-256 Integrity Hash", heading_style))
            story.append(Paragraph(bundle.sha256_hash or "(not computed)", mono_style))
            story.append(Spacer(1, 6 * mm))

            # 6 — Disclaimer
            story.append(Paragraph(
                "DISCLAIMER: This document is an automated forensic estimate generated by "
                "Bharat Kavach AI. It does not constitute legal advice, a certified forensic "
                "examination report, or an official government document. All findings are "
                "informational and must be independently verified before use in legal proceedings.",
                disclaimer_style,
            ))

            doc.build(story)
            return pdf_path.resolve()

        except Exception as exc:
            raise PdfGenerationError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Convenience / caching
    # ------------------------------------------------------------------

    def get_or_create_bundle(self, case) -> EvidenceBundle:
        """
        Return a cached bundle for ``case`` if it already exists on disk,
        otherwise build, export, and cache a new one.
        """
        bundle_id = getattr(case, "bundle_id", None)
        if bundle_id:
            cached = self.EXPORTS_DIR / f"BK-{bundle_id}.evidence.json"
            if cached.exists():
                data = json.loads(cached.read_text(encoding="utf-8"))
                return EvidenceBundle(**data)

        # Build fresh bundle from case fields
        from ai_engines.behavioral import AnalysisResult
        bundle = self.build_bundle(
            case_id=case.id,
            transcript=getattr(case, "transcript", "") or "",
            behavioral_result=None,
            legal_findings=None,
            vision_result=None,
            currency_result=None,
            model_registry=None,
        )
        self.export_json(bundle)
        try:
            self.export_pdf(bundle)
        except PdfGenerationError:
            pass  # JSON export succeeded; PDF failure is non-fatal for the API response
        return bundle

    def get_pdf_path(self, bundle_id: str) -> Path:
        """
        Return the expected filesystem path for the PDF of a given bundle.
        Does NOT check whether the file actually exists.
        """
        return self.EXPORTS_DIR / f"BK-{bundle_id}.summary.pdf"
