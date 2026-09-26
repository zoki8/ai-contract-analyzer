from pdf_utils import normalize,extract_text,chunk
import sys
from llm import analyze_chunk
from schemas import Finding
import json

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

def analyze_text(text: str, on_progress=None )->list[dict]:

        parts=chunk(text)
        if on_progress:
                on_progress(0,len(parts))
        findings=[]
        for i,p in enumerate(parts,1):
            result = analyze_chunk(p)
            if on_progress:
                on_progress(i,len(parts))
            findings.extend(result.findings)

        findings=dedupe(findings)
        
        source=squash(text)
        out=[]

        for f in findings:
            d=f.model_dump()
            d["hallucinated"]=squash(f.quote) not in source
            out.append(d)
        return out

if __name__=="__main__":
    with open(sys.argv[1], "rb") as file:
        text=extract_text(file.read())
    out=analyze_text(text, lambda i,n: print(f"chunk {i}/{n}", file=sys.stderr))
    print(json.dumps(out, indent=2, ensure_ascii=False))




