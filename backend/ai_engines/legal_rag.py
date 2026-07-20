import json
import os
import time
from typing import List, Dict, Optional
from pydantic import BaseModel
from rapidfuzz import process, fuzz
from google import genai
from google.genai import types
from google.genai import types
from dotenv import load_dotenv

# Load .env from the backend directory regardless of cwd
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))


class LegalClaim(BaseModel):
    claim_extracted: str
    verdict: str  # confirmed_false, unverifiable, plausible
    explanation: str
    matched_kb_id: Optional[str]
    relevant_provision: Optional[str]
    disclaimer: str = "Informational — not legal advice"


class LegalVerificationResult(BaseModel):
    verifications: List[LegalClaim]


class LegalRAG:
    def __init__(self, api_key: str, kb_path: str = None):
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.1-flash-lite"

        # Default KB path: <backend_root>/data/legal_kb.json
        # Works regardless of the cwd the process is launched from.
        if kb_path is None:
            kb_path = os.path.join(_BACKEND_DIR, "data", "legal_kb.json")

        try:
            with open(kb_path, "r") as f:
                self.kb = json.load(f)
        except FileNotFoundError:
            self.kb = []
            print(f"Warning: Legal KB not found at {kb_path}")

    def _generate(self, prompt: str, response_schema=None, retries: int = 3) -> str:
        """Call the Gemini API with simple retry on rate-limit (429)."""
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
                    import re as _re
                    m = _re.search(r'retry_delay.*?seconds:\s*(\d+)', err, _re.DOTALL)
                    if not m:
                        m = _re.search(r'seconds:\s*(\d+)', err)
                    delay = int(m.group(1)) + 2 if m else 60
                    print(f"[LegalRAG] Rate limited. Waiting {delay}s before retry {attempt + 2}/{retries}...")
                    time.sleep(delay)
                else:
                    raise
        raise RuntimeError("All retries exhausted")

    def _extract_claims(self, transcript: str) -> List[str]:
        """Step 1: Extract discrete legal claims from the transcript."""
        prompt = f"""
        Extract a list of specific legal assertions or threats made by the speaker in the following transcript.
        Focus on claims about arrest procedures, legal sections, identity of authorities, or financial demands to settle cases.
        Return ONLY a JSON list of strings.

        Transcript: {transcript}
        """
        try:
            claims_schema = {
                "type": "array",
                "items": {"type": "string"},
            }
            text = self._generate(prompt, response_schema=claims_schema)
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0].strip() if "```json" in text else text.split("```")[1].split("```")[0].strip()
            claims = json.loads(text)
            return claims if isinstance(claims, list) else []
        except Exception as e:
            print(f"Claim extraction failed: {e}")
            return []

    def _match_claim(self, claim: str) -> Optional[Dict]:
        """Step 2: Hybrid Retrieval (keyword/fuzzy match first)."""
        if not self.kb:
            return None

        claim_lower = claim.lower()
        patterns = [item["scam_claim_pattern"] for item in self.kb]

        # Pass 0: Keyword pre-filter — high-signal domain terms mapped to KB IDs.
        # This ensures paraphrased claims that contain key phrases are caught
        # even when fuzzy similarity to the full pattern is moderate.
        KEYWORD_HINTS = {
            "digital_arrest_myth_1": ["digital arrest", "digitally arrest", "arrest digitally"],
            "financial_settlement_myth_1": ["upi", "transfer money", "pay to avoid", "settle the case", "compliance fee"],
            "fake_warrant_myth_1": ["warrant on whatsapp", "warrant on your whatsapp", "warrant via whatsapp", "warrant on phone"],
            "public_servant_impersonation_1": ["cbi officer", "ed officer", "calling from cbi", "calling from ed"],
            "digital_confinement_myth_1": ["do not disconnect", "don't disconnect", "dont disconnect", "do not tell anyone"],
        }
        for kb_id, keywords in KEYWORD_HINTS.items():
            if any(kw in claim_lower for kw in keywords):
                match = next((item for item in self.kb if item["id"] == kb_id), None)
                if match:
                    return match

        # Pass 1: RapidFuzz WRatio — best general-purpose scorer
        all_scores = process.extract(claim, patterns, scorer=fuzz.WRatio, limit=len(patterns))
        # Filter to only genuinely high scores (>= 78) to avoid false positives
        candidates = [(match, score, idx) for match, score, idx in all_scores if score >= 78]
        if candidates:
            # Pick the best scoring match
            best_match, best_score, best_idx = candidates[0]
            return self.kb[best_idx]

        # Pass 2: Semantic Fallback via LLM
        kb_summary = "\n".join([f"[{i}] {item['scam_claim_pattern']}" for i, item in enumerate(self.kb)])
        prompt = f"""
        Which of these legal knowledge base patterns best matches the claim: "{claim}"?
        Return ONLY the index number, or "NONE" if there is no strong match.

        Knowledge Base Patterns:
        {kb_summary}
        """
        try:
            result = self._generate(prompt)
            result = result.strip()
            if result.isdigit():
                idx = int(result)
                if 0 <= idx < len(self.kb):
                    return self.kb[idx]
        except Exception:
            pass

        return None

    def verify_legal_claims(self, transcript: str) -> List[LegalClaim]:
        """Main pipeline: Extract -> Match -> Strictly Grounded Explanation."""
        claims = self._extract_claims(transcript)
        results = []

        for claim_text in claims:
            match = self._match_claim(claim_text)

            if match:
                # Step 3: Strictly Grounded Explanation
                prompt = f"""
                You are a legal auditor. A potential scammer has made the following claim: "{claim_text}"

                You must verify this against our verified legal fact:
                Pattern: {match['scam_claim_pattern']}
                Reality: {match['reality']}
                Provision: {match['relevant_provision']}

                Instruction: Write a concise (1-2 sentences) explanation of why this claim is a myth or inaccurate.
                CRITICAL: Use ONLY the provided 'Reality' and 'Provision' information.
                DO NOT cite any other legal sections. If the provision is 'Informational', do not invent a section number.
                """
                try:
                    explanation_schema = {
                        "type": "object",
                        "properties": {"explanation": {"type": "string"}},
                        "required": ["explanation"],
                    }
                    raw = self._generate(prompt, response_schema=explanation_schema)
                    if "```" in raw:
                        raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.split("```")[1].split("```")[0].strip()
                    explanation = json.loads(raw).get("explanation", raw)

                    # Determine disclaimer based on bns_verified flag
                    bns_verified = match.get("bns_verified", False)
                    if not bns_verified:
                        disclaimer = (
                            "Citation not yet verified against current BNS/BNSS statute "
                            "— treat as informational"
                        )
                    else:
                        disclaimer = "Informational — not legal advice"

                    results.append(LegalClaim(
                        claim_extracted=claim_text,
                        verdict="confirmed_false",
                        explanation=explanation,
                        matched_kb_id=match["id"],
                        relevant_provision=match["relevant_provision"],
                        disclaimer=disclaimer,
                    ))
                except Exception:
                    continue
            else:
                results.append(LegalClaim(
                    claim_extracted=claim_text,
                    verdict="unverifiable",
                    explanation="No specific matched legal myth found in our database for this claim.",
                    matched_kb_id=None,
                    relevant_provision=None
                ))

        return results


if __name__ == "__main__":
    KEY = os.getenv("GOOGLE_API_KEY")
    if KEY:
        rag = LegalRAG(api_key=KEY)
        test_transcript = "You are under digital arrest. Transfer 50000 rupees via UPI to clear your name or you will be jailed."
        print(rag.verify_legal_claims(test_transcript))
