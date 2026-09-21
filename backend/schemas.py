from typing import Literal
from pydantic import BaseModel

class Finding(BaseModel):
    category: Literal['penalty', 'payment_terms','auto_renewal','termination','liability','other']
    severity: Literal['low','medium','high']
    quote:str
    explanation:str

class ChunkAnalysis(BaseModel):
    findings: list[Finding]
    