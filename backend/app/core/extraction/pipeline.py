"""Extraction pipeline orchestration: parse → pre-split → validate."""

from __future__ import annotations

from app.core.extraction.presplit import pre_split_blocks
from app.core.extraction.validator import BlockValidator
from app.core.extraction.schemas import ExtractionJobResult
from app.core.retrieval.product_match import suggest_product


class ExtractionPipeline:
    def __init__(self, language: str = "pl", use_llm: bool = False):
        self.language = language
        self.validator = BlockValidator(language=language, use_llm=use_llm)

    def run(self, text: str, auto_detect: bool = False) -> ExtractionJobResult:
        blocks = pre_split_blocks(text)
        requirements = []
        for idx, block in enumerate(blocks):
            requirements.extend(self.validator.validate(block, idx))

        product_suggestion = None
        auto_warning = False
        if auto_detect and requirements:
            corpus = "\n".join(r.text for r in requirements)
            product_suggestion, auto_warning = suggest_product(corpus)

        return ExtractionJobResult(
            requirements=requirements,
            blocks_processed=len(blocks),
            product_suggestion=product_suggestion,
            auto_detect_warning=auto_warning,
        )
