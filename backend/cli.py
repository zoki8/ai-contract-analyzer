from pdf_utils import normalize,extract_text,chunk
import sys
from llm import analyze_chunk
from schemas import Finding

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


if __name__=="__main__":
    with open(sys.argv[1], "rb") as file:
        text=extract_text(file.read())
    parts=chunk(text)
    findings=[]
    for i,p in enumerate(parts,1):
        print(f"chunk {i}/{len(parts)}...", file=sys.stderr)
        result = analyze_chunk(p)
        findings.extend(result.findings)

    findings=dedupe(findings)
    
    source=squash(text)
    out=[]

    for f in findings:
        d=f.model_dump()
        d["hallucinated"]=squash(f) not in source
        out.append(d)

    print(json.dumps(out, indent=2, ensure_ascii=False))





