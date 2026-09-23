from pypdf import PdfReader
import io
import re

def extract_text(data: bytes) ->str:
    reader=PdfReader(io.BytesIO(data))
    return "\n".join(p.extract_text() or "" for p in reader.pages).strip()

def normalize(data: str) -> str:
    s=re.sub("-\n","",data)
    s=s.split()
    s=" ".join(p for p in s)
    return s.lower()

def chunk_text(data: str)->list[str]:
    parts= re.split(r"(?=Section \d+|Article \d+|Član \d+)", data, flags=re.IGNORECASE)
    sections=[]
    for p in parts:
        if p.strip():
            sections.append(p)
    return sections

def pack(sections: list[str], max_chars: int, overlap: int) -> list[str]:
    chunks = []
    cur = ""
    for s in sections:
        if len(s)>max_chars:
            if cur:
                chunks.append(cur)
                cur=""
            chunks.extend(_split_chars(s,max_chars,overlap))
        elif len(s)+len(cur)>max_chars:
            if cur:
                chunks.append(cur)
            cur = s
        else: 
            cur+=s
    if cur:
        chunks.append(cur)
    return chunks
        
def _split_chars(text: str, max_chars:int, overlap:int)->list[str]:
    start=0
    conclusion=[]
    if overlap>=max_chars:
        raise ValueError("Overlap must be smaller than max_chars!!!")
    while start<len(text):
        end=min(len(text),start+max_chars)
        slice=text[start:end]
        conclusion.append(slice)
        if end==len(text):
            break
        start+=len(slice)-overlap
    return conclusion

def chunk(text:str, max_chars:int=6000, overlap:int=500)->list[str]:
    return pack(chunk_text,max_chars,overlap)



