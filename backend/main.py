import threading
import uuid

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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


def update(job_id: str, **fields):
    with LOCK:
        JOBS[job_id].update(fields)


def run_job(job_id: str, text: str):
    source = squash(text)
    chunks = chunk_text(text)
    update(job_id, status="running", total=len(chunks), done=0)
    findings = []
    try:
        for i, chunk in enumerate(chunks, 1):
            findings.extend(analyze_chunk(chunk).findings)
            update(job_id, done=i)
    except requests.ConnectionError:
        return update(job_id, status="error", error="Ollama is not running.")
    except requests.HTTPError as e:
        return update(job_id, status="error", error=f"Model error: {e}")
    except ValidationError:
        return update(job_id, status="error", error="Model returned invalid output.")
    except Exception as e:
        return update(job_id, status="error", error=f"Unexpected error: {e}")

    out = []
    for f in dedupe(findings):
        d = f.model_dump()
        d["hallucinated"] = squash(f.quote) not in source
        out.append(d)
    update(
        job_id,
        status="done",
        result={"findings": out, "disclaimer": DISCLAIMER},
    )


@app.post("/analyze-contract", status_code=202)
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

    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id] = {"status": "queued", "done": 0, "total": 0}
    threading.Thread(target=run_job, args=(job_id, text), daemon=True).start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with LOCK:
        job = JOBS.get(job_id)
        if job is None:
            raise HTTPException(404, "Unknown job.")
        return dict(job)
