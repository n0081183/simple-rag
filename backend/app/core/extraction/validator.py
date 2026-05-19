"""LLM block validator — structured JSON per pre-split block."""

from __future__ import annotations

import logging
import re

from pydantic import ValidationError

from app.core.extraction.prompts import block_validate_system
from app.core.extraction.schemas import (
    BlockValidationResult,
    ExtractedRequirement,
    RequirementCategory,
    RequirementPriority,
)
from app.core.llm import get_llm_provider

logger = logging.getLogger(__name__)


class BlockValidator:
    def __init__(self, language: str = "pl", use_llm: bool = True):
        self.language = language
        self.use_llm = use_llm
        self._llm = get_llm_provider() if use_llm else None

    def validate(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        if self.use_llm and self._llm:
            reqs = self._validate_llm(block, block_index)
            if reqs:
                return reqs
        return self._validate_heuristic(block, block_index)

    def _validate_heuristic(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        modal = re.search(r"\b(musi|muszą|shall|must|wymaga)\b", block, re.IGNORECASE)
        if not modal and len(block) < 40:
            return []
        title = " ".join(block.split()[:8])[:60]
        return [
            ExtractedRequirement(
                title=title,
                text=block.strip(),
                category=RequirementCategory.functional,
                priority=RequirementPriority.unknown,
                source_block_index=block_index,
            )
        ]

    def _validate_llm(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        system = block_validate_system(self.language)
        user = f"BLOCK:\n{block[:2000]}"
        raw = self._llm.complete_json(system, user, BlockValidationResult) if self._llm else {}

        try:
            result = BlockValidationResult.model_validate(raw)
        except ValidationError:
            # Fallback: parse REQ: lines from text response
            return self._parse_req_lines(block, block_index)

        if not result.is_requirement:
            return []

        texts = result.split_into or [block.strip()]
        reqs: list[ExtractedRequirement] = []
        cat = RequirementCategory.other
        try:
            cat = RequirementCategory(result.category) if hasattr(result, "category") else cat
        except (ValueError, TypeError):
            pass

        pri = RequirementPriority.unknown
        extra = raw if isinstance(raw, dict) else {}
        if extra.get("category"):
            try:
                cat = RequirementCategory(str(extra["category"]))
            except ValueError:
                pass
        if extra.get("priority"):
            try:
                pri = RequirementPriority(str(extra["priority"]))
            except ValueError:
                pass

        for text in texts:
            text = text.strip()
            if len(text) < 15:
                continue
            title = extra.get("title") or " ".join(text.split()[:6])
            reqs.append(
                ExtractedRequirement(
                    title=str(title)[:80],
                    text=text,
                    category=cat,
                    priority=pri,
                    source_block_index=block_index,
                )
            )
        return reqs

    def _parse_req_lines(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        """Legacy v3 line protocol fallback."""
        if self._llm:
            system = block_validate_system(self.language)
            text = self._llm.complete_text(system, f"BLOCK:\n{block[:2000]}")
        else:
            text = ""
        reqs = []
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("REQ:"):
                body = line[4:].strip()
                if body:
                    reqs.append(
                        ExtractedRequirement(
                            title=" ".join(body.split()[:6])[:80],
                            text=body,
                            source_block_index=block_index,
                        )
                    )
        if not reqs and re.search(r"\b(musi|must|shall)\b", block, re.I):
            return self._validate_heuristic(block, block_index)
        return reqs
