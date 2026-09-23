from fastapi import FastAPI, UploadFile, File, HTTPException
from pdf_utils import extract_text
from cli import analyze_text
import uuid
import threading

MAX_SIZE=10*1024*1024
JOBS = {}
LOCK = threading.Lock()

app=FastAPI()

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    with LOCK:
        if job_id not in JOBS:
            raise HTTPException(404, "Unknown job")
        return JOBS[job_id]

def run_job(job_id: str, text: str):
    with LOCK:
        JOBS[job_id] = {"status": "running"}
    try:
        result = analyze_text(text)
        with LOCK:
            JOBS[job_id] = {"status": "done","result": result}
    except Exception as e:
        with LOCK:
            JOBS[job_id] = {"status": "error","error": str(e)}

@app.post("/analyze-contract")
def analyze_contract(file: UploadFile=File(...)):
    data=file.file.read(MAX_SIZE+1)
    if len(data)>MAX_SIZE:
        raise HTTPException(413,"File too large (max 10MB)")
    if not data.startswith(b'%PDF-'):
        raise HTTPException(400,"Only PDFs are supported")
    try:
        text=extract_text(data)
    except Exception:
        raise HTTPException(422,"Could not read PDF")
    if len(text)<200:
        raise HTTPException(422,"PDF has no text (it may be a scan)")

    job_id = uuid.uuid4().hex
    with LOCK:
        JOBS[job_id]={"status": "queued"}
    threading.Thread(target=run_job, args=(job_id, text), daemon=True).start()
    return {"job_id":job_id}
