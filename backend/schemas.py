from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

PLACEHOLDER_QUOTES = {"n/a", "not applicable", "none", "null"}


class Finding(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: Literal[
        "penalty", "payment_terms", "auto_renewal",
        "termination", "liability", "other",
    ]
    severity: Literal["low", "medium", "high"]
    quote: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    @field_validator("quote")
    @classmethod
    def quote_not_placeholder(cls, v: str) -> str:
        if v.lower().rstrip(".") in PLACEHOLDER_QUOTES:
            raise ValueError(
                "quote must be copied from the contract, not a placeholder"
            )
        return v


class ChunkAnalysis(BaseModel):
    findings: list[Finding]
