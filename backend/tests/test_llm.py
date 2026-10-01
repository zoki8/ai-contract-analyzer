import json
from unittest.mock import MagicMock, patch

import pytest
import requests

import llm
from llm import ChunkAnalysisError, analyze_chunk

GOOD = {
    "findings": [
        {
            "category": "penalty",
            "severity": "high",
            "quote": "5% per day",
            "explanation": "Big penalty.",
        }
    ]
}
BAD = {
    "findings": [
        {
            "category": "fees",  # nije u Literal-u
            "severity": "high",
            "quote": "5% per day",
            "explanation": "Big penalty.",
        }
    ]
}


def fake_response(payload):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"message": {"content": json.dumps(payload)}}
    return r


@pytest.fixture(autouse=True)
def no_sleep():
    with patch("llm.time.sleep"):
        yield


def test_success_first_try():
    with patch("llm.requests.post", return_value=fake_response(GOOD)) as post:
        result = analyze_chunk("some text")
    assert post.call_count == 1
    assert result.findings[0].category == "penalty"


def test_empty_findings_is_valid():
    with patch("llm.requests.post", return_value=fake_response({"findings": []})):
        assert analyze_chunk("text").findings == []


def test_invalid_then_valid_retries_with_error_message():
    with patch(
        "llm.requests.post",
        side_effect=[fake_response(BAD), fake_response(GOOD)],
    ) as post:
        result = analyze_chunk("text")

    assert post.call_count == 2
    assert result.findings[0].category == "penalty"

    second_messages = post.call_args_list[1].kwargs["json"]["messages"]
    assert second_messages[-1]["role"] == "user"
    assert "invalid" in second_messages[-1]["content"]
    assert second_messages[-2]["role"] == "assistant"


def test_always_invalid_raises_after_max_attempts():
    with patch("llm.requests.post", return_value=fake_response(BAD)) as post:
        with pytest.raises(ChunkAnalysisError):
            analyze_chunk("text")
    assert post.call_count == llm.MAX_ATTEMPTS


def test_network_error_then_success():
    with patch(
        "llm.requests.post",
        side_effect=[requests.ConnectionError("down"), fake_response(GOOD)],
    ) as post:
        result = analyze_chunk("text")
    assert post.call_count == 2
    assert len(result.findings) == 1


def test_network_error_every_time_raises():
    with patch("llm.requests.post", side_effect=requests.Timeout("slow")) as post:
        with pytest.raises(ChunkAnalysisError):
            analyze_chunk("text")
    assert post.call_count == llm.MAX_ATTEMPTS
