import os
import pytest
from ai_engines.legal_rag import LegalRAG
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def rag():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not found")
    return LegalRAG(api_key=api_key)

def test_paraphrased_digital_arrest(rag):
    """Test if paraphrased claims about digital arrest are caught."""
    transcript = "You are being put under a digital arrest by the CBI right now. Don't end this video call."
    results = rag.verify_legal_claims(transcript)
    
    assert len(results) > 0
    # Find the digital arrest claim
    digital_arrest_claims = [r for r in results if r.matched_kb_id == "digital_arrest_myth_1"]
    assert len(digital_arrest_claims) > 0
    assert "BNSS Section 43" in digital_arrest_claims[0].relevant_provision
    assert digital_arrest_claims[0].verdict == "confirmed_false"

def test_negative_control_legit_statement(rag):
    """Test that legitimate legal statements are not flagged as confirmed myths."""
    transcript = "You should report this incident to the cybercrime portal at cybercrime.gov.in."
    results = rag.verify_legal_claims(transcript)
    
    for r in results:
        # It shouldn't match any of our myth patterns
        assert r.verdict != "confirmed_false" or r.matched_kb_id is None

def test_hallucination_prevention(rag):
    """Test that the LLM doesn't invent section numbers for unknown claims."""
    transcript = "You have violated the International Cookie Protocol section 999."
    results = rag.verify_legal_claims(transcript)
    
    for r in results:
        if r.verdict == "unverifiable":
            assert r.relevant_provision is None
        # Even if it matches something else, it shouldn't contain "999" unless it's in our KB
        assert "999" not in (r.explanation or "")

def test_upi_extortion_claim(rag):
    """Test if UPI payment threats are flagged."""
    transcript = "Transfer 25000 to this UPI ID or a warrant will be served on your WhatsApp."
    results = rag.verify_legal_claims(transcript)
    
    # Check for UPI/extortion match
    upi_matches = [r for r in results if r.matched_kb_id == "financial_settlement_myth_1"]
    # Check for fake warrant match
    warrant_matches = [r for r in results if r.matched_kb_id == "fake_warrant_myth_1"]
    
    assert len(upi_matches) > 0 or len(warrant_matches) > 0

if __name__ == "__main__":
    # If running manually
    pytest.main([__file__])
