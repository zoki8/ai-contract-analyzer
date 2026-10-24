from pdf_utils import normalize,extract_text,chunk
import sys
from llm import analyze_chunk, ChunkAnalysisError
from schemas import Finding
import json
from difflib import SequenceMatcher

def squash(s: str)->str:
    return normalize(s).replace(" ","")


SEVERITY = {"low": 0, "medium": 1, "high": 2}


def squash_map(text: str) -> tuple[str, list[int]]:
    """Like squash(text), but also remembers where every kept character was in the
    original text, so a span in the squashed text can be cut out of the original."""
    chars, where = [], []
    i = 0
    while i < len(text):
        if text.startswith("-\n", i):      # word hyphenated across lines, as in normalize()
            i += 2
            continue
        if not text[i].isspace():
            for ch in text[i].lower():
                chars.append(ch)
                where.append(i)
        i += 1
    return "".join(chars), where


def same_clause(a: Finding, b: Finding, span_a, span_b) -> bool:
    """Same category and either one quote contains the other, or both quotes
    cover an overlapping part of the contract (two pieces of a clause cut in half)."""
    if a.category != b.category:
        return False
    qa, qb = squash(a.quote), squash(b.quote)
    if qa in qb or qb in qa:
        return True
    if span_a and span_b:
        overlap = min(span_a[1], span_b[1]) - max(span_a[0], span_b[0])
        return overlap >= MIN_FUZZY
    return False


def dedupe(findings: list[Finding], source: str | None = None) -> list[Finding]:
    """Merge findings that describe the same clause. With the source text, two
    overlapping pieces of one clause are merged into one quote cut from the contract."""
    if source is not None:
        squashed, where = squash_map(source)
    kept = []  # (finding, span in the squashed source or None)
    for f in findings:
        span = locate(squash(f.quote), squashed) if source is not None else None
        for i, (k, kspan) in enumerate(kept):
            if not same_clause(f, k, span, kspan):
                continue
            longer = f if len(f.quote) > len(k.quote) else k
            severity = max(f.severity, k.severity, key=SEVERITY.get)
            if span and kspan:
                start, end = min(span[0], kspan[0]), max(span[1], kspan[1])
                original = source[where[start] : where[end - 1] + 1].replace("-\n", "")
                merged = longer.model_copy(update={"quote": " ".join(original.split()),
                                                   "severity": severity})
                kept[i] = (merged, (start, end))
            else:
                kept[i] = (longer.model_copy(update={"severity": severity}), kspan or span)
            break
        else:
            kept.append((f, span))
    return [f for f, _ in kept]

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

    findings=dedupe(findings, text)

    source=squash(text)
    out=[]

    for f in findings:
        d=f.model_dump()
        d["hallucinated"] = not appears_in(squash(f.quote), source)
        out.append(d)
    return out

MIN_FUZZY = 20      # quotes shorter than this must match exactly
SIMILARITY = 0.9    # share of characters that must agree for a near-verbatim quote


def locate(quote: str, text: str) -> tuple[int, int] | None:
    """Where quote is in text, word for word or almost word for word, as (start, end).
    None if it is not there. Both arguments are expected to be squashed."""
    pos = text.find(quote)
    if pos != -1:
        return pos, pos + len(quote)
    if len(quote) < MIN_FUZZY:
        return None
    anchor = SequenceMatcher(None, text, quote, autojunk=False).find_longest_match(
        0, len(text), 0, len(quote)
    )
    start = max(0, anchor.a - anchor.b)
    window = text[start : start + len(quote) + len(quote) // 10]
    if SequenceMatcher(None, window, quote, autojunk=False).ratio() >= SIMILARITY:
        return start, start + len(quote)
    return None


def appears_in(quote: str, text: str) -> bool:
    """True if quote appears in text word for word, or almost word for word.
    Both arguments are expected to be squashed."""
    return locate(quote, text) is not None

if __name__=="__main__":
    with open(sys.argv[1], "rb") as file:
        text=extract_text(file.read())
    failed=[]
    out=analyze_text(text, lambda i,n: print(f"chunk {i}/{n}", file=sys.stderr), failed)
    if failed:
        print(f"WARNING: {len(failed)} chunk(s) could not be analyzed: {failed}", file=sys.stderr)
    print(json.dumps(out, indent=2, ensure_ascii=False))
