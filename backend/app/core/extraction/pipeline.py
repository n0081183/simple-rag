"""Extraction pipeline: pre-split → parallel LLM validation."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.config import get_settings
from app.core.extraction.presplit import pre_split_blocks
from app.core.extraction.validator import BlockValidator
from app.core.extraction.schemas import ExtractionJobResult, ExtractedRequirement
from app.core.retrieval.product_match import detect_products, suggest_product
from app.core.extraction.schemas import ProductSuggestionOut

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    def __init__(self, language: str = "pl", use_llm: bool = True, max_workers: int = 4):
        self.language = language
        self.validator = BlockValidator(language=language, use_llm=use_llm)
        settings = get_settings()
        self.max_workers = max_workers if use_llm else 1

    def run(self, text: str, auto_detect: bool = False) -> ExtractionJobResult:
        blocks = pre_split_blocks(text)
        requirements: list[ExtractedRequirement] = []

        if len(blocks) <= 1 or self.max_workers == 1:
            for idx, block in enumerate(blocks):
                requirements.extend(self.validator.validate(block, idx))
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                futures = {
                    pool.submit(self.validator.validate, block, idx): idx
                    for idx, block in enumerate(blocks)
                }
                for fut in as_completed(futures):
                    try:
                        requirements.extend(fut.result())
                    except Exception as e:
                        logger.warning("block_validate_failed error=%s", e)

        product_suggestion = None
        product_suggestions: list[ProductSuggestionOut] = []
        auto_warning = False
        if auto_detect and requirements:
            corpus = "\n".join(r.text for r in requirements)
            ranked = detect_products(corpus, top_n=3)
            product_suggestions = [
                ProductSuggestionOut(
                    product=s.product,
                    score=s.score,
                    lexical_score=s.lexical_score,
                    semantic_score=s.semantic_score,
                )
                for s in ranked
            ]
            product_suggestion, auto_warning = suggest_product(corpus)

        return ExtractionJobResult(
            requirements=requirements,
            blocks_processed=len(blocks),
            product_suggestion=product_suggestion,
            product_suggestions=product_suggestions,
            auto_detect_warning=auto_warning,
            status="completed",
        )
