import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from pdf_utils import extract_text, chunk_text
from llm import analyze_chunk
from cli import dedupe, squash

MAX_SIZE = 10 * 1024 * 1024  # 10 MB
DISCLAIMER = "Automated analysis. Not legal advice."

app = FastAPI(title="AI Contract Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:1420"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


@app.post("/analyze-contract")
def analyze_contract(file: UploadFile = File(...)):
    data = file.file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 10 MB).")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Only PDF files are supported.")

    try:
        text = extract_text(data)
    except Exception:
        raise HTTPException(422, "Could not read the PDF.")
    if len(text) < 200:
        raise HTTPException(422, "PDF has no text (it may be a scan).")

    source = squash(text)
    findings = []
    try:
        for chunk in chunk_text(text):
            findings.extend(analyze_chunk(chunk).findings)
    except requests.ConnectionError:
        raise HTTPException(503, "Ollama is not running.")
    except requests.HTTPError as e:
        raise HTTPException(502, f"Model error: {e}")
    except ValidationError:
        raise HTTPException(502, "Model returned invalid output.")

    out = []
    for f in dedupe(findings):
        d = f.model_dump()
        d["hallucinated"] = squash(f.quote) not in source
        out.append(d)
    return {"findings": out, "disclaimer": DISCLAIMER}