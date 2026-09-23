import requests
from schemas import ChunkAnalysis

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:7b"

SYSTEM = (
    "You are a contract review assistant. From the given part of a contract, "
    "extract risky clauses: penalties, payment terms, auto-renewal, termination "
    "conditions, and limitations of liability. For each finding give the EXACT "
    "quote copied from the text, a severity (low, medium, high), and a short "
    "explanation of why it is risky. If there are no risky clauses, return an "
    "empty list. Do not invent clauses that are not in the text."
)
def analyze_chunk(text: str)->ChunkAnalysis:
    payload = {
        "model":MODEL,
        "stream":False,
        "format":ChunkAnalysis.model_json_schema(),
        "options": {"num_ctx":8192,"temperature":0},
        "messages":[
            {"role": "system" , "content" : SYSTEM},
            {"role": "user" , "content" : text}
        ]
    }
    r=requests.post(OLLAMA_URL, json=payload, timeout=300)
    r.raise_for_status()
    return ChunkAnalysis.model_validate_json(r.json()["message"]["content"])

