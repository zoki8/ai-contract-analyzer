import io
import pytest
from pypdf import PdfWriter

from pdf_utils import chunk, chunk_text, extract_text, normalize, pack, _split_chars


# ---------- chunk_text ----------

def test_splits_on_headings_after_sentence_end():
    text = "Section 1. Payment is due. Section 2. Termination applies."
    parts = chunk_text(text)
    assert len(parts) == 2
    assert parts[0].startswith("Section 1")
    assert parts[1].strip().startswith("Section 2")


def test_cross_reference_does_not_split():
    text = "Fees are due as set out in Section 5. Late fees apply."
    assert len(chunk_text(text)) == 1


def test_no_headings_returns_single_chunk():
    assert chunk_text("Just a plain paragraph without headings.") == [
        "Just a plain paragraph without headings."
    ]


def test_empty_text():
    assert chunk_text("") == []


def test_articles_and_serbian_headings():
    text = "Article 1. Foo. Član 2. Bar."
    assert len(chunk_text(text)) == 2


def test_heading_match_is_case_insensitive():
    # normalize() pretvara sve u mala slova
    text = "section 1. foo. section 2. bar."
    assert len(chunk_text(text)) == 2


# ---------- pack ----------

def test_small_sections_are_merged():
    assert pack(["aaa", "bbb"], max_chars=10, overlap=2) == ["aaabbb"]


def test_sections_start_new_chunk_when_full():
    result = pack(["aaaaa", "bbbbb", "ccccc"], max_chars=10, overlap=2)
    assert result == ["aaaaabbbbb", "ccccc"]


def test_long_section_flushes_current_chunk_first():
    result = pack(["short ", "x" * 25], max_chars=10, overlap=2)
    assert result[0] == "short "
    assert all(len(c) <= 10 for c in result)


# ---------- _split_chars ----------

def test_split_chars_overlap_and_no_loss():
    text = "".join(str(i % 10) for i in range(25))
    chunks = _split_chars(text, max_chars=10, overlap=2)
    assert all(len(c) <= 10 for c in chunks)
    assert chunks[0][-2:] == chunks[1][:2]
    rebuilt = chunks[0] + "".join(c[2:] for c in chunks[1:])
    assert rebuilt == text


def test_overlap_not_smaller_than_max_raises():
    with pytest.raises(ValueError):
        _split_chars("abcdef", max_chars=5, overlap=5)


# ---------- chunk (ceo tok) ----------

def test_chunk_respects_max_chars_and_keeps_all_headings():
    text = "".join(
        f"Section {i}. Payment is due in {i} days. " for i in range(1, 21)
    )
    chunks = chunk(text, max_chars=100, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)
    joined = " ".join(chunks)
    assert all(f"Section {i}." in joined for i in range(1, 21))


def test_short_text_is_one_chunk_identical_to_input():
    text = "Section 1. a. Section 2. b."
    assert chunk(text, max_chars=6000, overlap=500) == [text]


# ---------- normalize ----------

def test_normalize_joins_hyphenation_and_collapses_whitespace():
    assert normalize("Hel-\nlo   World\n\nFoo") == "hello world foo"


def test_normalize_keeps_inline_hyphens():
    assert normalize("A 30-day period") == "a 30-day period"


# ---------- extract_text ----------

def test_blank_pdf_returns_empty_string():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    assert extract_text(buf.getvalue()) == ""
