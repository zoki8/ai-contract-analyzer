"""Unit tests for the parts of the pipeline that do not need the model.

Run from the backend folder:  pytest -v
Ollama does not have to be running: nothing here calls the model.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cli import appears_in, dedupe, squash
from main import MAX_SIZE, app
from pdf_utils import _split_chars, chunk, chunk_text, extract_text, normalize, pack
from run_eval import is_flagged, is_found
from schemas import Finding

TEST_PDF = Path(__file__).parent.parent / "eval" / "contracts" / "test.pdf"


def finding(category: str, quote: str) -> Finding:
    return Finding(category=category, severity="high", quote=quote, explanation="x")


# ---------- extract_text ----------

def test_extract_text_reads_all_sections():
    text = extract_text(TEST_PDF.read_bytes())
    for heading in ["Section 1", "Section 2", "Section 3", "Section 4"]:
        assert heading in text


# ---------- normalize / squash ----------

def test_normalize_collapses_whitespace_and_lowercases():
    assert normalize("The  Client\n  shall\tPAY") == "the client shall pay"


def test_normalize_joins_words_hyphenated_across_lines():
    assert normalize("ugo-\nvor") == "ugovor"


def test_squash_ignores_spacing_differences():
    # the model often returns a quote with slightly different spacing than the PDF
    assert squash("5 % per day") == squash("5%  per\nday")


# ---------- chunk_text ----------

def test_chunk_text_splits_before_each_heading_and_keeps_it():
    sections = chunk_text("Section 1. A\nfoo\nSection 2. B\nbar")
    assert len(sections) == 2
    assert sections[0].startswith("Section 1")
    assert sections[1].startswith("Section 2")


def test_chunk_text_handles_article_and_clan_in_any_case():
    sections = chunk_text("Član 1\nabc\nČLAN 2\ndef\nArticle 3\nxyz")
    assert len(sections) == 3


def test_chunk_text_loses_no_text():
    text = "Intro\nSection 1. A\nfoo\nSection 2. B\nbar"
    assert "".join(chunk_text(text)) == text


@pytest.mark.xfail(reason="known limitation: a heading mentioned inside a sentence also splits")
def test_chunk_text_does_not_split_on_mid_sentence_reference():
    text = "Section 4. Termination\nThe Supplier may terminate as described in Section 2 above."
    assert len(chunk_text(text)) == 1


# ---------- _split_chars ----------

def test_split_chars_lengths_with_overlap():
    parts = _split_chars("x" * 25, 10, 3)
    assert [len(p) for p in parts] == [10, 10, 10, 4]


def test_split_chars_consecutive_parts_overlap():
    text = "".join(chr(ord("a") + i) for i in range(20))  # "abcdefghijklmnopqrst"
    parts = _split_chars(text, 8, 3)
    for prev, nxt in zip(parts, parts[1:]):
        assert prev[-3:] == nxt[:3]


def test_split_chars_rejects_overlap_not_smaller_than_limit():
    with pytest.raises(ValueError):
        _split_chars("x" * 25, 10, 10)


# ---------- pack / chunk ----------

def test_pack_groups_small_sections_up_to_the_limit():
    sections = ["a" * 40, "b" * 30, "c" * 50, "d" * 20, "e" * 70]
    assert [len(c) for c in pack(sections, 100, 20)] == [70, 70, 70]


def test_pack_splits_an_oversized_section_and_keeps_order():
    sections = ["a" * 40, "b" * 250, "c" * 30]
    chunks = pack(sections, 100, 20)
    assert [len(c) for c in chunks] == [40, 100, 100, 90, 30]
    assert chunks[0] == "a" * 40
    assert chunks[-1] == "c" * 30


def test_pack_keeps_every_section_exactly_once_when_nothing_is_oversized():
    sections = ["s1 ", "s2 ", "s3 ", "s4 "]
    assert "".join(pack(sections, 7, 2)) == "".join(sections)


def test_chunk_never_exceeds_max_chars():
    text = "Section 1. A\n" + "word " * 3000 + "\nSection 2. B\nshort"
    assert all(len(c) <= 1000 for c in chunk(text, 1000, 100))


# ---------- dedupe ----------

def test_dedupe_keeps_the_longer_quote():
    short = finding("penalty", "penalty of 5% per day")
    long = finding("penalty", "The Client shall pay a penalty of 5% per day.")
    assert dedupe([short, long]) == [long]


def test_dedupe_keeps_same_quote_in_different_categories():
    a = finding("penalty", "5% per day")
    b = finding("termination", "5% per day")
    assert len(dedupe([a, b])) == 2


def test_dedupe_keeps_unrelated_findings():
    a = finding("penalty", "5% per day")
    b = finding("penalty", "fee of 100 EUR")
    assert len(dedupe([a, b])) == 2


# ---------- evaluation matching ----------

FINDINGS = [{"category": "penalty", "quote": "The Client shall pay a penalty of 5% per day."}]


def test_is_found_needs_same_category_and_quote():
    assert is_found({"category": "penalty", "quote_contains": "5% per day"}, FINDINGS)
    assert not is_found({"category": "termination", "quote_contains": "5% per day"}, FINDINGS)


def test_is_flagged_ignores_category_case_and_spacing():
    assert is_flagged({"quote_contains": "5% PER  day"}, FINDINGS)
    assert not is_flagged({"quote_contains": "laws of Serbia"}, FINDINGS)


def test_is_found_accepts_a_list_of_alternatives():
    expected = {"category": "penalty", "quote_contains": ["something else", "5% per day"]}
    assert is_found(expected, FINDINGS)


def test_is_found_when_model_quotes_part_of_a_longer_labelled_clause():
    clause = "Late payment. The Client shall pay a penalty of 5% per day. Interest accrues monthly."
    assert is_found({"category": "penalty", "quote_contains": clause}, FINDINGS)


def test_a_very_short_model_quote_does_not_match_a_long_clause():
    short = [{"category": "penalty", "quote": "5%"}]
    clause = "The Client shall pay a penalty of 5% per day for late payment."
    assert not is_found({"category": "penalty", "quote_contains": clause}, short)


# ---------- API validation ----------

client = TestClient(app)


def upload(data: bytes):
    return client.post("/analyze-contract", files={"file": ("f.pdf", data, "application/pdf")})


def test_api_rejects_non_pdf():
    assert upload(b"hello, not a pdf").status_code == 400


def test_api_rejects_too_large_file():
    assert upload(b"%PDF-" + b"0" * MAX_SIZE).status_code == 413


def test_api_rejects_unreadable_pdf():
    assert upload(b"%PDF-1.4 broken").status_code == 422


def test_api_accepts_real_pdf_and_returns_job_id():
    response = upload(TEST_PDF.read_bytes())
    assert response.status_code == 200
    assert len(response.json()["job_id"]) == 32


def test_api_unknown_job_is_404():
    assert client.get("/jobs/does-not-exist").status_code == 404


# ---------- near-verbatim quotes ----------

SOURCE = squash(
    "12. Term. This Agreement shall automatically be renewed for one (1) or more "
    "one (1) month periods unless either party gives written notice of non-renewal."
)


def test_appears_in_accepts_exact_quote():
    assert appears_in(squash("automatically be renewed for one (1) or more"), SOURCE)


def test_appears_in_accepts_quote_with_one_word_changed():
    quote = "This Agreement will automatically be renewed for one (1) or more one (1) month periods"
    assert appears_in(squash(quote), SOURCE)


def test_appears_in_rejects_invented_sentence():
    assert not appears_in(squash("Not applicable in the provided text."), SOURCE)
    assert not appears_in(squash("The Supplier may terminate at any time without notice."), SOURCE)


def test_appears_in_short_quote_must_be_exact():
    assert not appears_in(squash("one (2) month"), SOURCE)
