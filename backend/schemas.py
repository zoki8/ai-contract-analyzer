from typing import Literal
from pydantic import BaseModel

class Finding(BaseModel):
    category:Literal['penalty','payment_terms','auto_renewal','termination','liability','other']
    severity:Literal['low','medium','high']
    quote:str
    explanation:str

class ChunkAnalysis(BaseModel):
    findings:list[Finding]

if __name__=="__main__":
    ok = {"findings": [{"category": "penalty", "severity": "high",
                    "quote": "5% per day", "explanation": "Big penalty."}]}
    print(ChunkAnalysis.model_validate(ok))

    bad = {"findings": [{"category": "fees", "severity": "high",
                     "quote": "5% per day", "explanation": "Big penalty."}]}
    print(ChunkAnalysis.model_validate(bad))
