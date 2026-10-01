from pdf_utils import normalize,extract_text,chunk
import sys
from llm import analyze_chunk, ChunkAnalysisError
from schemas import Finding
import json
from difflib import SequenceMatcher

def squash(s: str)->str:
    return normalize(s).replace(" ","")


def dedupe(findings: list[Finding]) -> list[Finding]:
    kept=[]
    for f in findings:
        found=False
        for i,k in enumerate(kept):
            if f.category==k.category:
                if (squash(k.quote) in squash(f.quote)) or (squash(f.quote) in squash(k.quote)):
                    found=True
                    if len(f.quote)>len(k.quote):
                        kept[i]=f
                    break
        if not found:
            kept.append(f)
    return kept

def analyze_text(text: str, on_progress=None, failed_chunks: list[int] | None = None)->list[dict]:
    """Analyze a contract. Chunks that still fail after all LLM retries are skipped;
    their 1-based numbers are appended to failed_chunks (if a list is passed in)."""
    parts=chunk(text)
    if on_progress:
        on_progress(0,len(parts))
    findings=[]
    for i,p in enumerate(parts,1):
        try:
            result = analyze_chunk(p)
        except ChunkAnalysisError as e:
            if failed_chunks is not None:
                failed_chunks.append(i)
            print(f"chunk {i}/{len(parts)} skipped: {e}", file=sys.stderr)
        else:
            findings.extend(result.findings)
        if on_progress:
            on_progress(i,len(parts))

    findings=dedupe(findings)

    source=squash(text)
    out=[]

    for f in findings:
        d=f.model_dump()
        d["hallucinated"] = not appears_in(squash(f.quote), source)
        out.append(d)
    return out

MIN_FUZZY = 20      # quotes shorter than this must match exactly
SIMILARITY = 0.9    # share of characters that must agree for a near-verbatim quote


def appears_in(quote: str, text: str) -> bool:
    """True if quote appears in text word for word, or almost word for word.
    Both arguments are expected to be squashed."""
    if quote in text:
        return True
    if len(quote) < MIN_FUZZY:
        return False
    anchor = SequenceMatcher(None, text, quote, autojunk=False).find_longest_match(
        0, len(text), 0, len(quote)
    )
    start = max(0, anchor.a - anchor.b)
    window = text[start : start + len(quote) + len(quote) // 10]
    return SequenceMatcher(None, window, quote, autojunk=False).ratio() >= SIMILARITY

if __name__=="__main__":
    with open(sys.argv[1], "rb") as file:
        text=extract_text(file.read())
    failed=[]
    out=analyze_text(text, lambda i,n: print(f"chunk {i}/{n}", file=sys.stderr), failed)
    if failed:
        print(f"WARNING: {len(failed)} chunk(s) could not be analyzed: {failed}", file=sys.stderr)
    print(json.dumps(out, indent=2, ensure_ascii=False))
