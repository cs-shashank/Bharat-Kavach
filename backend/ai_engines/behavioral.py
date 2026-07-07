import os
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class ScamStage(Enum):
    NORMAL = "Normal Conversation"
    AUTHORITY = "Authority Impersonation (CBI/Police/NCB)"
    ISOLATION = "Digital Confinement / Isolation (Don't tell family)"
    EVIDENCE = "Fabricated Evidence / Illegal Acts"
    URGENCY = "Urgency / Fear Injection"
    DEMAND = "Financial Demand / UPI Request"

class AnalysisResult(BaseModel):
    current_stage: str = Field(description="The detected stage from the ScamStage enum")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of why this stage was detected")
    red_flags: List[str] = Field(description="Specific phrases or behaviors that triggered the alert")
    intervention_required: bool = Field(description="Whether the system should trigger a bank/police hold")

class BehavioralClassifier:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.1
        )
        self.parser = JsonOutputParser(pydantic_object=AnalysisResult)
        
    def analyze_transcript(self, transcript: str) -> AnalysisResult:
        template = """
        You are a Forensic Cybercrime Analyst specializing in Indian "Digital Arrest" scams.
        Analyze the following transcript segment and classify it based on the Scam Escalation Arc.

        SCAM STAGES:
        1. Normal Conversation: Casual talk, no threats.
        2. Authority Impersonation: Caller claims to be from CBI, Police, Custom, RBI, or NCB.
        3. Digital Confinement / Isolation: Caller tells victim to stay on video call, not tell family, or stay in a room.
        4. Fabricated Evidence: Claims of illegal parcels, drugs, Aadhaar misuse, or money laundering.
        5. Urgency / Fear Injection: Threatening immediate arrest, social shame, or jail time.
        6. Financial Demand: Asking for a 'security deposit', 'verification fee', or UPI transfer.

        TRANSCRIPT:
        {transcript}

        {format_instructions}
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm | self.parser
        
        result_dict = chain.invoke({
            "transcript": transcript,
            "format_instructions": self.parser.get_format_instructions()
        })
        
        return AnalysisResult(**result_dict)

# Example usage for testing (Mock)
if __name__ == "__main__":
    # In production, use os.getenv("GOOGLE_API_KEY")
    mock_transcript = "Stay on this Skype call. Do not tell your wife or anyone. If you close the camera, CBI will arrest you immediately at your home."
    # classifier = BehavioralClassifier(api_key="YOUR_KEY")
    # print(classifier.analyze_transcript(mock_transcript))
    print("BehavioralClassifier initialized.")
