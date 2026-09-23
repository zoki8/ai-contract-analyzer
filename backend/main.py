from fastapi import FastAPI, UploadFile, File
from pdf_utils import extract_text
from cli import analyze_text

app=FastAPI()

@app.get("/hello")
def hello():
    return {"poruka":"radi"}


@app.post("/analyze-contract")
def analyze_contract(file: UploadFile=File(...)):
    data=file.file.read()
    text=extract_text(data)
    return {"findings":analyze_text(text)}
