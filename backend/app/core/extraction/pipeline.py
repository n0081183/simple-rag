"""Extraction pipeline: fast heuristic on all blocks, optional LLM refine."""

from __future__ import annotations

import logging
from collections import defaultdict

from app.config import get_settings
from app.core.extraction.presplit import _has_requirement_keyword, pre_split_blocks
from app.core.extraction.validator import BlockValidator
from app.core.extraction.schemas import ExtractionJobResult, ExtractedRequirement
from app.core.retrieval.product_match import detect_products, suggest_product
from app.core.extraction.schemas import ProductSuggestionOut

logger = logging.getLogger(__name__)


class ExtractionPipeline:
    def __init__(self, language: str = "pl", use_llm: bool | None = None):
        settings = get_settings()
        if use_llm is None:
            use_llm = settings.extraction_use_llm
        self.language = language
        self.use_llm = use_llm
        self.validator = BlockValidator(language=language, use_llm=use_llm)
        self.max_llm_blocks = settings.extraction_max_llm_blocks

    def run(self, text: str, auto_detect: bool = False) -> ExtractionJobResult:
        blocks = pre_split_blocks(text)
        if not blocks:
            return ExtractionJobResult(
                requirements=[],
                blocks_processed=0,
                status="completed",
                error="No text blocks found in document",
            )

        by_block: dict[int | None, list[ExtractedRequirement]] = defaultdict(list)
        for idx, block in enumerate(blocks):
            for req in self.validator.validate_heuristic(block, idx):
                by_block[idx].append(req)

        llm_refined = 0
        if self.use_llm:
            for idx, block in enumerate(blocks):
                if llm_refined >= self.max_llm_blocks:
                    break
                if not _has_requirement_keyword(block):
                    continue
                llm_reqs = self.validator.validate_llm(block, idx)
                llm_refined += 1
                if llm_reqs:
                    by_block[idx] = llm_reqs
                elif not by_block[idx]:
                    by_block[idx] = self.validator.validate_heuristic(block, idx)

        requirements: list[ExtractedRequirement] = []
        for idx in sorted(by_block.keys(), key=lambda x: (x is None, x or 0)):
            requirements.extend(by_block[idx])

        mode = "heuristic+llm" if self.use_llm else "heuristic"
        logger.info(
            "extraction_done mode=%s blocks=%d requirements=%d llm_calls=%d",
            mode,
            len(blocks),
            len(requirements),
            llm_refined,
        )

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

        warning = None
        if not requirements and blocks:
            warning = (
                "No requirements detected. Try a document with 'musi/must/shall' "
                "or enable LLM extraction in Settings (slower)."
            )

        return ExtractionJobResult(
            requirements=requirements,
            blocks_processed=len(blocks),
            product_suggestion=product_suggestion,
            product_suggestions=product_suggestions,
            auto_detect_warning=auto_warning,
            status="completed",
            error=warning,
        )
