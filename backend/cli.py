from pdf_utils import normalize


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

