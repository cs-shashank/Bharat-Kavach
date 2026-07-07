import json
import os
from typing import List, Dict, Optional
from pydantic import BaseModel
from rapidfuzz import process, fuzz
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

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
    def __init__(self, api_key: str, kb_path: str = "backend/data/legal_kb.json"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load KB
        absolute_kb_path = os.path.join(os.getcwd(), kb_path)
        try:
            with open(absolute_kb_path, "r") as f:
                self.kb = json.load(f)
        except FileNotFoundError:
            self.kb = []
            print(f"Warning: Legal KB not found at {absolute_kb_path}")

    def _extract_claims(self, transcript: str) -> List[str]:
        """Step 1: Extract discrete legal claims from the transcript."""
        prompt = f"""
        Extract a list of specific legal assertions or threats made by the speaker in the following transcript.
        Focus on claims about arrest procedures, legal sections, identity of authorities, or financial demands to settle cases.
        Return ONLY a JSON list of strings.
        
        Transcript: {transcript}
        """
        try:
            response = self.model.generate_content(prompt)
            # Basic parsing of JSON from LLM response
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            claims = json.loads(text)
            return claims if isinstance(claims, list) else []
        except Exception as e:
            print(f"Claim extraction failed: {e}")
            return []

    def _match_claim(self, claim: str) -> Optional[Dict]:
        """Step 2: Hybrid Retrieval (keyword/fuzzy match first)."""
        if not self.kb:
            return None
        
        patterns = [item["scam_claim_pattern"] for item in self.kb]
        
        # Pass 1: RapidFuzz (Keyword/Fuzzy)
        best_match = process.extractOne(claim, patterns, scorer=fuzz.partial_ratio)
        
        if best_match and best_match[1] > 80:
            index = patterns.index(best_match[0])
            return self.kb[index]
            
        # Pass 2: Semantic Fallback (using LLM to identify matching KB entry)
        # We search for the most relevant entry index
        kb_summary = "\n".join([f"[{i}] {item['scam_claim_pattern']}" for i, item in enumerate(self.kb)])
        prompt = f"""
        Which of these legal knowledge base patterns best matches the claim: "{claim}"?
        Return ONLY the index number, or "NONE" if there is no strong match.
        
        Knowledge Base Patterns:
        {kb_summary}
        """
        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            if result.isdigit():
                idx = int(result)
                if 0 <= idx < len(self.kb):
                    return self.kb[idx]
        except:
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
                    response = self.model.generate_content(prompt)
                    explanation = response.text.strip()
                    
                    # Validation: Ensure no halluncinated sections (check if explanation contains numbers not in Provision)
                    # For simplicity, we just trust the prompt's strong constraint but could add regex checks.
                    
                    results.append(LegalClaim(
                        claim_extracted=claim_text,
                        verdict="confirmed_false",
                        explanation=explanation,
                        matched_kb_id=match["id"],
                        relevant_provision=match["relevant_provision"]
                    ))
                except:
                    continue
            else:
                # Unverifiable or Plausible (if it didn't match any known myths)
                results.append(LegalClaim(
                    claim_extracted=claim_text,
                    verdict="unverifiable",
                    explanation="No specific matched legal myth found in our database for this claim.",
                    matched_kb_id=None,
                    relevant_provision=None
                ))
                
        return results

if __name__ == "__main__":
    # Quick Test
    KEY = os.getenv("GOOGLE_API_KEY")
    if KEY:
        rag = LegalRAG(api_key=KEY)
        test_transcript = "You are under digital arrest. Transfer 50000 rupees via UPI to clear your name or you will be jailed."
        print(rag.verify_legal_claims(test_transcript))
