# AI Contract Analyzer

An AI-powered tool that reviews PDF contracts and flags risky clauses —
penalties, payment terms, auto-renewal, termination conditions, and
liability limits — with an exact quote and a short explanation for each.

> **Automated analysis. Not legal advice.**

## What it does

1. Upload a PDF contract.
2. The backend extracts the text, splits it into sections, and sends each
   section to a local LLM (via Ollama).
3. The model returns structured findings (category, severity, quote,
   explanation), validated against a strict schema.
4. Duplicate findings from overlapping sections are merged, and each quote
   is checked against the source text to flag possible hallucinations.
5. Results are shown in the browser as cards, with a live progress bar.

## Architecture

    React + TS (upload)
      | POST /analyze-contract  ->  202 Accepted, returns job_id
      v
    FastAPI
      1. validate file type (magic bytes) and size
      2. pypdf: extract text
      3. split into sections (with char-based fallback + overlap)
      4. background thread: for each section -> LLM -> JSON  --->  llm.py -> Ollama
      5. validate (Pydantic), merge duplicates, check quotes against source
      | GET /jobs/{job_id}  ->  progress, then final result
      v
    React + TS (progress bar, then finding cards)

The LLM call lives behind a single function (llm.py), so the model can be
swapped without touching the rest of the code.

## Project structure

    ai-contract-analyzer/
    ├── backend/
    │   ├── main.py         # FastAPI app: upload endpoint + job polling
    │   ├── llm.py           # Ollama call, the only model-dependent code
    │   ├── pdf_utils.py     # text extraction, normalization, chunking
    │   ├── schemas.py       # Pydantic models for findings
    │   ├── cli.py           # PDF -> JSON from the command line
    │   ├── run_eval.py      # evaluation script (recall, hallucination rate)
    │   └── requirements.txt
    ├── frontend/            # Vite + React + TypeScript
    ├── eval/
    │   ├── contracts/       # sample contracts (PDF)
    │   └── expected/        # expected findings (JSON)
    └── README.md

## Running it locally

1. Install and start Ollama, then pull a model:

       curl -fsSL https://ollama.com/install.sh | sh
       ollama pull qwen2.5:7b

2. Backend:

       cd backend
       python -m venv .venv
       source .venv/bin/activate
       pip install -r requirements.txt
       uvicorn main:app --port 8000 --reload

3. Frontend (in a separate terminal):

       cd frontend
       npm install
       npm run dev

Open http://localhost:5173, upload a PDF, and click **Analyze contract**.

## Evaluation

run_eval.py runs the pipeline against a small set of sample contracts and
checks the model's findings against manually labeled expected findings.

    cd backend
    python run_eval.py

Latest run (2 contracts, qwen2.5:7b):

| Metric | Result |
|---|---|
| Recall | 5/6 (83%) |
| Hallucinated quotes | 0 |

The one miss: the model classified a late-payment penalty clause as
`payment_terms` instead of `penalty`. The two categories are semantically
close, and the system prompt doesn't yet draw a hard line between them.

## Known limitations

- **Category overlap:** `penalty` and `payment_terms` can be ambiguous to
  the model (see evaluation above).
- **Chunking:** sections are split on `Section N` / `Article N` headings,
  with a fallback to character-based splitting for very long sections.
  Contracts with unusual numbering may split poorly.
- **In-memory jobs:** job status is stored in memory and is lost on server
  restart.
- **No OCR:** scanned (image-only) PDFs are rejected.
- **Single language tested:** evaluated on English contracts; quality on
  other languages depends on the underlying model.

## Not legal advice

This tool provides an automated, best-effort analysis for informational
purposes only. It is not a substitute for review by a qualified lawyer.
