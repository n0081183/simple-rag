"""LLM block validator — structured output per pre-split block."""

from __future__ import annotations

from app.core.extraction.schemas import BlockValidationResult, ExtractedRequirement, RequirementCategory, RequirementPriority


class BlockValidator:
    """Validates a single block; Milestone 0 uses heuristic mock, M1 wires Ollama."""

    def __init__(self, language: str = "pl", use_llm: bool = False):
        self.language = language
        self.use_llm = use_llm

    def validate(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        if self.use_llm:
            return self._validate_llm(block, block_index)
        return self._validate_heuristic(block, block_index)

    def _validate_heuristic(self, block: str, block_index: int) -> list[ExtractedRequirement]:
        """Mock validator: treat blocks with modal verbs as requirements."""
        import re

        modal = re.search(
            r"\b(musi|muszą|shall|must|wymaga)\b", block, re.IGNORECASE
        )
        if not modal and len(block) < 40:
            return []

        title_words = block.split()[:8]
        title = " ".join(title_words)
        if len(title) > 60:
            title = title[:57] + "..."

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
        # Milestone 1: Ollama + BlockValidationResult JSON schema
        result = BlockValidationResult(
            is_requirement=True,
            split_into=[block.strip()],
        )
        if not result.is_requirement:
            return []
        reqs = []
        for i, text in enumerate(result.split_into or [block]):
            title = " ".join(text.split()[:6])
            reqs.append(
                ExtractedRequirement(
                    title=title,
                    text=text,
                    source_block_index=block_index,
                )
            )
        return reqs
