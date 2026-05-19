"""Structured verification output schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    MET = "MET"
    PARTIAL = "PARTIAL"
    NOT_MET = "NOT_MET"
    UNCLEAR = "UNCLEAR"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceItem(BaseModel):
    source_file: str
    topic_url: str
    quote: str
    relevance: str = "medium"  # high | medium | low


class TerminologyMapping(BaseModel):
    siwz_term: str
    product_term: str


class VerificationResult(BaseModel):
    requirement_id: str
    requirement_text: str
    verdict: Verdict
    reasoning_steps: list[str] = Field(min_length=1, max_length=8)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    confidence: Confidence
    caveats: str | None = None
    terminology_mapping: list[TerminologyMapping] = Field(default_factory=list)
    product_auto_detected: bool = False
