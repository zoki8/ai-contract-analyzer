from pypdf import PdfReader
import io
import re

# Seče pre "Section N" / "Article N" / "Član N" samo ako je to naslov:
# na početku teksta ili odmah posle kraja rečenice. Upućivanja tipa
# "see Section 5" se ne seku.
HEADING_SPLIT = re.compile(
    r"(?:(?<=[.;:])|(?<=\n)|^)(?=\s*(?:Section|Article|Član)\s+\d+)",
    flags=re.IGNORECASE,
)


def extract_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join(p.extract_text() or "" for p in reader.pages).strip()


def normalize(data: str) -> str:
    s = re.sub("-\n", "", data)
    s = s.split()
    s = " ".join(p for p in s)
    return s.lower()


def chunk_text(data: str) -> list[str]:
    parts = HEADING_SPLIT.split(data)
    return [p for p in parts if p.strip()]


def pack(sections: list[str], max_chars: int, overlap: int) -> list[str]:
    chunks = []
    cur = ""
    for s in sections:
        if len(s) > max_chars:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.extend(_split_chars(s, max_chars, overlap))
        elif len(s) + len(cur) > max_chars:
            if cur:
                chunks.append(cur)
            cur = s
        else:
            cur += s
    if cur:
        chunks.append(cur)
    return chunks


def _split_chars(text: str, max_chars: int, overlap: int) -> list[str]:
    if overlap >= max_chars:
        raise ValueError("Overlap must be smaller than max_chars!!!")
    start = 0
    pieces = []
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end]
        pieces.append(piece)
        if end == len(text):
            break
        start += len(piece) - overlap
    return pieces


def chunk(text: str, max_chars: int = 6000, overlap: int = 500) -> list[str]:
    return pack(chunk_text(text), max_chars, overlap)
