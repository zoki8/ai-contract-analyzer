from fastapi import FastAPI, UploadFile, File, HTTPException
from pdf_utils import extract_text
from cli import analyze_text

MAX_SIZE=10*1024*1024

app=FastAPI()

@app.get("/hello")
def hello():
    return {"poruka":"radi"}


@app.post("/analyze-contract")
def analyze_contract(file: UploadFile=File(...)):
    data=file.file.read(MAX_SIZE+1)
    if len(data)>MAX_SIZE:
        raise HTTPException(413,"File too large (max 10GB)")
    if not data.startswith(b'%PDF-'):
        raise HTTPException(400,"Only PDFs are supported")
    try:
        text=extract_text(data)
    except Exception:
        raise HTTPException(422,"Could not read PDF")
    if len(text)<200:
        raise HTTPException(422,"PDF has no text (it may be a scan)")
    return {"findings":analyze_text(text)}
