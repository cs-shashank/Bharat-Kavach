from typing import List, Dict

class ProtocolVerifier:
    """
    Checks for procedural violations in government and law enforcement interactions.
    If a protocol is violated, it indicates a high probability of a scam.
    """
    
    PROTOCOLS = {
        "VIDEO_ARREST": {
            "rule": "Indian law enforcement (CBI, ED, Police, NCB) NEVER conducts arrests or interrogations via video calls.",
            "severity": "CRITICAL"
        },
        "UPI_PAYMENT": {
            "rule": "Government agencies NEVER ask for money transfers via UPI, QR codes, or gift cards for 'verification' or 'fines'.",
            "severity": "CRITICAL"
        },
        "WHATSAPP_WARRANT": {
            "rule": "Official warrants are NEVER served via WhatsApp, Skype, or Telegram DM.",
            "severity": "HIGH"
        },
        "DIGITAL_CONFINEMENT": {
            "rule": "Agencies never ask a citizen to stay in 'digital confinement' or keep a camera on continuously.",
            "severity": "CRITICAL"
        }
    }

    def check_violations(self, transcript: str, metadata: Dict = None) -> List[Dict]:
        """
        Scans a transcript for specific protocol violations.
        In a production system, this could also use the LLM to verify these rules are being broken.
        """
        violations = []
        transcript_lower = transcript.lower()

        # Rule 1: Video Arrest
        if any(x in transcript_lower for x in ["skype", "video call", "zoom", "stays on camera"]):
            if any(x in transcript_lower for x in ["arrest", "investigation", "interrogation"]):
                violations.append(self.PROTOCOLS["VIDEO_ARREST"])

        # Rule 2: UPI / Payment
        if any(x in transcript_lower for x in ["upi", "qr code", "gpay", "phonepe", "transfer money", "security deposit"]):
            violations.append(self.PROTOCOLS["UPI_PAYMENT"])

        # Rule 3: Digital Confinement
        if any(x in transcript_lower for x in ["don't tell anyone", "lock your room", "stay alone"]):
            violations.append(self.PROTOCOLS["DIGITAL_CONFINEMENT"])

        return violations

# Example usage
if __name__ == "__main__":
    verifier = ProtocolVerifier()
    test_transcript = "You must pay a security deposit of 50,000 via GPay to clear your name from this money laundering case."
    print(verifier.check_violations(test_transcript))
