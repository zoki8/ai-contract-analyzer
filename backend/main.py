from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import requests
import threading
import uuid

from pdf_utils import extract_text
from cli import analyze_text
from db import engine, Job, init_db

MAX_SIZE = 10 * 1024 * 1024
init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "tauri://localhost", "http://tauri.localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "Unknown job")
        return {
            "status": job.status,
            "done": job.done,
            "total": job.total,
            "result": job.result,
            "error": job.error,
        }


def update_job(job_id: str, **fields):
    with Session(engine) as s:
        s.query(Job).filter(Job.id == job_id).update(fields)
        s.commit()


def run_job(job_id: str, text: str):
    update_job(job_id, status="running")

    def progress(i, n):
        update_job(job_id, done=i, total=n)

    try:
        result = analyze_text(text, progress)
        update_job(job_id, status="done", result=result)
    except requests.ConnectionError:
        update_job(job_id, status="error",
                   error="Ollama is not running. Start it with: ollama serve")
    except Exception as e:
        update_job(job_id, status="error", error=str(e))


@app.post("/analyze-contract")
def analyze_contract(file: UploadFile = File(...)):
    data = file.file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise HTTPException(413, "File too large (max 10MB)")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "Only PDFs are supported")
    try:
        text = extract_text(data)
    except Exception:
        raise HTTPException(422, "Could not read PDF")
    if len(text) < 200:
        raise HTTPException(422, "PDF has no text (it may be a scan)")

    job_id = uuid.uuid4().hex
    with Session(engine) as s:
        s.add(Job(id=job_id, status="queued"))
        s.commit()
    threading.Thread(target=run_job, args=(job_id, text), daemon=True).start()
    return {"job_id": job_id}