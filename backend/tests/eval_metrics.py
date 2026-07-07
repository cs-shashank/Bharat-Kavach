import os
import json
from typing import List, Dict
from ai_engines.behavioral import BehavioralClassifier
from ai_engines.legal_rag import LegalRAG
from ai_engines.protocol import ProtocolVerifier
from dotenv import load_dotenv

load_dotenv()

class EvaluationFramework:
    def __init__(self, api_key: str):
        self.classifier = BehavioralClassifier(api_key=api_key)
        self.legal_rag = LegalRAG(api_key=api_key)
        self.verifier = ProtocolVerifier()
        
    def run_eval(self, test_cases: List[Dict]):
        results = []
        for case in test_cases:
            transcript = case["transcript"]
            expected_label = case["label"] # scam or legit
            
            # Run pipeline
            beh_analysis = self.classifier.analyze_transcript(transcript)
            legal_findings = self.legal_rag.verify_legal_claims(transcript)
            violations = self.verifier.check_violations(transcript)
            
            # Decision Logic for Evaluation
            # A case is predicted as 'scam' if risk score > 60 or legal myths detected or protocol violations found
            myths_found = any(f.verdict == "confirmed_false" for f in legal_findings)
            prediction = "scam" if (beh_analysis.risk_score > 60 or myths_found or len(violations) > 0) else "legit"
            
            results.append({
                "id": case["id"],
                "expected": expected_label,
                "predicted": prediction,
                "risk_score": beh_analysis.risk_score,
                "myths_detected": myths_found,
                "violations_count": len(violations)
            })
            
        return results

    def calculate_metrics(self, results: List[Dict]):
        tp = sum(1 for r in results if r["expected"] == "scam" and r["predicted"] == "scam")
        tn = sum(1 for r in results if r["expected"] == "legit" and r["predicted"] == "legit")
        fp = sum(1 for r in results if r["expected"] == "legit" and r["predicted"] == "scam")
        fn = sum(1 for r in results if r["expected"] == "scam" and r["predicted"] == "legit")
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        return {
            "total_samples": len(results),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "false_positive_rate": round(fpr, 4),
            "confusion_matrix": {"tp": tp, "tn": tn, "fp": fp, "fn": fn}
        }

if __name__ == "__main__":
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if not API_KEY:
        print("Error: GOOGLE_API_KEY missing.")
        exit(1)
        
    # Expanded Forensic Dataset (40 Detailed Samples)
    test_cases = [
        # SCAMS: Digital Arrest / Authority
        {"id": "scam_1", "label": "scam", "transcript": "FedEx: Your parcel with passport 123X has been seized. Talk to CBI officer now. You are under digital arrest."},
        {"id": "scam_2", "label": "scam", "transcript": "I am DCP Mumbai. Stay on the video call. Do not tell anyone. Show your house on camera for safety audit."},
        {"id": "scam_3", "label": "scam", "transcript": "CBI Alert: Your Aadhaar linked to money laundering. Move to a quiet room for interrogation. Don't hide anything."},
        {"id": "scam_4", "label": "scam", "transcript": "ED Officer speaking. We found illegal transactions in your Canara Bank account. Pay 20k to avoid immediate raid."},
        {"id": "scam_5", "label": "scam", "transcript": "NCRB: Your IP is being used for child pornography. Pay the settlement fine via this UPI link to avoid FIR."},
        
        # SCAMS: Financial Extraction
        {"id": "scam_6", "label": "scam", "transcript": "Your son has been arrested. Send 50k immediately via PhonePe to clear his name. Case will be closed by tonight."},
        {"id": "scam_7", "label": "scam", "transcript": "KBC: You won 25 Lakhs! Pay 30,000 for Tax and Processing before the prize is released to your bank."},
        {"id": "scam_8", "label": "scam", "transcript": "Electricity Dept: Your power will be cut in 2 hours. Call 98XX now to pay pending bill of 15k via link."},
        {"id": "scam_9", "label": "scam", "transcript": "Amazon Refund: We owe you 5k. Download AnyDesk so we can process the payment to your wallet live."},
        {"id": "scam_10", "label": "scam", "transcript": "TRAI: Your SIM will be blocked in 1 hour. Press 9. You need to pay 2,000 to verify your KYC details."},

        # LEGIT: Banking / Transactional
        {"id": "legit_1", "label": "legit", "transcript": "Hello, I am calling from ICICI bank for home loan inquiry. Is this a good time to talk? No payment needed."},
        {"id": "legit_2", "label": "legit", "transcript": "IRCTC: Your train 12952 is running late by 30 mins. We apologize for the delay. Check NTES for live status."},
        {"id": "legit_3", "label": "legit", "transcript": "Swiggy Support: Your order 101 was delayed. I have initiated a refund of 50 rupees to your account."},
        {"id": "legit_4", "label": "legit", "transcript": "Zomato: Your delivery partner is outside. Please share the OTP for the order. Thank you for ordering."},
        {"id": "legit_5", "label": "legit", "transcript": "Airtel: Your data plan is about to expire. Recharge via Airtel Thanks app for 10% cashback. No urgency."},

        # LEGIT: Legal / Official (Negative Controls)
        {"id": "legit_6", "label": "legit", "transcript": "Saket District Court: You have a hearing scheduled for case 442/2024. Please appear with your lawyer."},
        {"id": "legit_7", "label": "legit", "transcript": "Passport Seva: Your physical police verification is scheduled for tomorrow. Please keep your originals ready."},
        {"id": "legit_8", "label": "legit", "transcript": "IT Dept: Your refund for AY 2023-24 has been processed. Check your registered bank account for credit."},
        {"id": "legit_9", "label": "legit", "transcript": "L&T Finance: Your EMI for the car loan is due on the 5th. Friendly reminder to keep sufficient balance."},
        {"id": "legit_10", "label": "legit", "transcript": "Voter Helpline: Please verify your name in the electoral rolls for the upcoming municipal elections."},

        # Diverse Scam & Legit Scenarios (Filling to 40)
        {"id": "scam_11", "label": "scam", "transcript": "Customs: Illegal parcel with your Aadhaar. Pay 18k 'Customs Duty' to avoid arrest warrant today."},
        {"id": "scam_12", "label": "scam", "transcript": "CBI Inspector: We have a warrant for your laptop's serial number. Pay 5k to prevent seizure."},
        {"id": "scam_13", "label": "scam", "transcript": "Your Netflix account is on hold. Update billing here: n3tflix-verify.com/login. Pay 1 rupee to verify."},
        {"id": "scam_14", "label": "scam", "transcript": "WhatsApp Support: Your account will be deleted for illegal activity. Share OTP to verify your identity."},
        {"id": "scam_15", "label": "scam", "transcript": "This is Mumbai Police. Your relative is in jail for an accident. Pay 40k via UPI to settle it now."},
        {"id": "scam_16", "label": "scam", "transcript": "Income Tax: We found fraud in your account. You need to pay 10,000 penalty immediately or face jail."},
        {"id": "scam_17", "label": "scam", "transcript": "Supreme Court: Stay of warrant possible if you pay 25k to the advocate's account now."},
        {"id": "scam_18", "label": "scam", "transcript": "I am calling from the Telecom Ministry. Your Aadhaar is misuse. Close your account by paying 1k."},
        {"id": "scam_19", "label": "scam", "transcript": "YouTube Reward: You won a car! Fill details on car-prize-2024.com and pay 500 delivery fee."},
        {"id": "scam_20", "label": "scam", "transcript": "Cyber Crime Dept: Your webcam was hijacked. Pay 50k in Bitcoin or I'll release your video to family."},
        {"id": "legit_11", "label": "legit", "transcript": "Hi, this is your Uber driver. I am outside the building. Please come down. I'm wearing a yellow shirt."},
        {"id": "legit_12", "label": "legit", "transcript": "Hey, I'm at the grocery store. Do you want milk or bread? I'll be home in 10 minutes. Love you."},
        {"id": "legit_13", "label": "legit", "transcript": "Your appointment with the dentist is confirmed for tomorrow at 5 PM. Reply YES to confirm."},
        {"id": "legit_14", "label": "legit", "transcript": "This is a reminder from the library: your book 'Cracking the Code' is overdue. Fine is 5 rupees."},
        {"id": "legit_15", "label": "legit", "transcript": "LinkedIn: Someone viewed your profile. Click to see the details of potential recruiters."},
        {"id": "legit_16", "label": "legit", "transcript": "Hello, this is Rohan from the office. Can you send the report for the Q1 sales by tomorrow morning?"},
        {"id": "legit_17", "label": "legit", "transcript": "Hi, I'm calling from your child's school. Just checking why they were absent today. Hope they're okay."},
        {"id": "legit_18", "label": "legit", "transcript": "This is an automated call from your gym. We're closed for maintenance on Sunday. Sorry for the inconvenience."},
        {"id": "legit_19", "label": "legit", "transcript": "LIC: Your life insurance policy is up for renewal. Please visit the branch or pay online via the portal."},
        {"id": "legit_20", "label": "legit", "transcript": "Courrier: I am at your door. Please share the delivery OTP to receive the package. Thank you."}
    ]
    
    framework = EvaluationFramework(api_key=API_KEY)
    print("Running Eval on 8 samples...")
    results = framework.run_eval(test_cases)
    metrics = framework.calculate_metrics(results)
    
    with open("backend/data/eval_results.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    print("Evaluation Complete. Results saved to backend/data/eval_results.json")
    print(json.dumps(metrics, indent=2))
