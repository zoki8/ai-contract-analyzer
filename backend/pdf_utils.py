import io
import re
from pypdf import PdfReader


def extract_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(p.extract_text() or "" for p in reader.pages).strip()


def normalize(s: str) -> str:
    """Collapse whitespace, fix hyphenated line breaks, lowercase.
    Used for comparing model quotes against the source text."""
    s = re.sub(r"-\n", "", s)
    return " ".join(s.split()).lower()


def _split_chars(text: str, max_chars: int, overlap: int) -> list[str]:
    out, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        out.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return out


def chunk_text(text: str, max_chars: int = 6000, overlap: int = 500) -> list[str]:
    # split before "Section 5" / "Article 5" headings
    parts = re.split(r"(?=\n\s*(?:Section|Article)\s+\d+)", text, flags=re.IGNORECASE)
    chunks, cur = [], ""
    for p in parts:
        if len(p) > max_chars:  # single section too long -> fall back to char split
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.extend(_split_chars(p, max_chars, overlap))
        elif len(cur) + len(p) > max_chars:
            chunks.append(cur)
            cur = p
        else:
            cur += p
    if cur.strip():
        chunks.append(cur)
    return chunks