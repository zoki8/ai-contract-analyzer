import sys
import json
from pdf_utils import extract_text, chunk_text, normalize
from llm import analyze_chunk


def squash(s: str) -> str:
    """Normalize and remove all spaces, so small spacing errors
    in model quotes don't count as hallucinations."""
    return normalize(s).replace(" ", "")


def dedupe(findings):
    kept = []
    for f in findings:
        c = squash(f.quote)
        for i, k in enumerate(kept):
            kc = squash(k.quote)
            if k.category == f.category and (c in kc or kc in c):
                if len(c) > len(kc):  # keep the longer quote
                    kept[i] = f
                break
        else:
            kept.append(f)
    return kept


if __name__ == "__main__":
    with open(sys.argv[1], "rb") as fh:
        text = extract_text(fh.read())
    source = squash(text)
    chunks = chunk_text(text)
    findings = []
    for i, ch in enumerate(chunks, 1):
        print(f"chunk {i}/{len(chunks)}...", file=sys.stderr)
        findings.extend(analyze_chunk(ch).findings)
    out = []
    for f in dedupe(findings):
        d = f.model_dump()
        d["hallucinated"] = squash(f.quote) not in source
        out.append(d)
    print(json.dumps(out, indent=2, ensure_ascii=False))