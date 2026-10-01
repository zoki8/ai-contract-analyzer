import pytest
from pydantic import ValidationError

from schemas import ChunkAnalysis


def finding(**overrides):
    base = {
        "category": "penalty",
        "severity": "high",
        "quote": "5% per day",
        "explanation": "Big penalty.",
    }
    base.update(overrides)
    return {"findings": [base]}


def test_valid_finding():
    result = ChunkAnalysis.model_validate(finding())
    assert result.findings[0].category == "penalty"


def test_empty_findings_is_valid():
    assert ChunkAnalysis.model_validate({"findings": []}).findings == []


def test_unknown_category_rejected():
    with pytest.raises(ValidationError):
        ChunkAnalysis.model_validate(finding(category="fees"))


@pytest.mark.parametrize("quote", ["", "   "])
def test_empty_quote_rejected(quote):
    with pytest.raises(ValidationError):
        ChunkAnalysis.model_validate(finding(quote=quote))


@pytest.mark.parametrize("quote", ["Not applicable", "N/A", "not applicable."])
def test_placeholder_quote_rejected(quote):
    with pytest.raises(ValidationError):
        ChunkAnalysis.model_validate(finding(quote=quote))


def test_whitespace_is_stripped():
    result = ChunkAnalysis.model_validate(finding(quote="  5% per day  "))
    assert result.findings[0].quote == "5% per day"
