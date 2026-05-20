"""Pydantic schemas for requirement extraction (structured LLM output)."""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class RequirementCategory(str, Enum):
    functional = "functional"
    non_functional = "non_functional"
    compatibility = "compatibility"
    security = "security"
    commercial = "commercial"
    other = "other"


class RequirementPriority(str, Enum):
    mandatory = "mandatory"
    scored = "scored"
    optional = "optional"
    unknown = "unknown"


class BlockValidationResult(BaseModel):
    is_requirement: bool
    reason_if_not: str | None = None
    split_into: list[str] = Field(default_factory=list)
    title: str | None = None
    category: RequirementCategory = RequirementCategory.other
    priority: RequirementPriority = RequirementPriority.unknown


class ExtractedRequirement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    text: str
    category: RequirementCategory = RequirementCategory.other
    priority: RequirementPriority = RequirementPriority.unknown
    enabled: bool = True
    source_block_index: int | None = None


class ProductSuggestionOut(BaseModel):
    product: str
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0


class ExtractionJobResult(BaseModel):
    requirements: list[ExtractedRequirement]
    blocks_processed: int = 0
    product_suggestion: str | None = None
    product_suggestions: list[ProductSuggestionOut] = Field(default_factory=list)
    auto_detect_warning: bool = False
    status: str = "completed"
    error: str | None = None
