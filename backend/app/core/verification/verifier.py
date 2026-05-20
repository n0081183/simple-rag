"""Per-requirement verification orchestration."""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.core.extraction.schemas import ExtractedRequirement
from app.core.llm import get_llm_provider
from app.core.reporting.anonymizer import anonymize_results
from app.core.retrieval.retriever import Retriever, build_context
from app.core.verification.prompts import build_verify_system_prompt, build_verify_user_prompt
from app.core.verification.schemas import (
    Confidence,
    EvidenceItem,
    VerificationResult,
    Verdict,
)

logger = logging.getLogger(__name__)


class VerificationOrchestrator:
    def __init__(self, product: str, language: str = "pl", anonymize: bool = False):
        self.product = product
        self.language = language
        self.anonymize = anonymize
        self.retriever = Retriever()
        self.llm = get_llm_provider()

    def verify_one(self, req: ExtractedRequirement) -> VerificationResult:
        chunks = self.retriever.retrieve(req.text, product_filter=self.product)
        context = build_context(chunks)
        system = build_verify_system_prompt(self.product, self.language)
        user = build_verify_user_prompt(req.text, context, self.language)

        raw = self.llm.complete_json(system, user, VerificationResult)
        try:
            result = VerificationResult(
                requirement_id=req.id,
                requirement_text=req.text,
                **{
                    k: v
                    for k, v in raw.items()
                    if k not in ("requirement_id", "requirement_text") and v is not None
                },
            )
        except (ValidationError, TypeError) as e:
            logger.warning("verify_parse_failed id=%s error=%s", req.id, e)
            return self._fallback_verify(req, chunks, no_evidence_policy=True)

        if not result.evidence:
            if result.verdict in (Verdict.MET, Verdict.PARTIAL, Verdict.NOT_MET):
                result.verdict = Verdict.UNCLEAR
                result.confidence = Confidence.LOW
                result.caveats = (result.caveats or "") + " Brak cytatu w kontekście."
            elif chunks:
                result.evidence = [
                    EvidenceItem(
                        source_file=c.source_file,
                        topic_url=c.topic_url,
                        quote=c.text[:400],
                        relevance="medium",
                    )
                    for c in chunks[:3]
                ]

        if self.anonymize:
            result = anonymize_results([result])[0]

        return result

    def verify_all(self, requirements: list[ExtractedRequirement]) -> list[VerificationResult]:
        return [self.verify_one(r) for r in requirements if r.enabled]

    def _fallback_verify(self, req, chunks, no_evidence_policy: bool = False) -> VerificationResult:
        evidence = [
            EvidenceItem(
                source_file=c.source_file,
                topic_url=c.topic_url,
                quote=c.text[:400],
                relevance="medium",
            )
            for c in chunks[:3]
        ]
        if no_evidence_policy and not evidence:
            verdict = Verdict.UNCLEAR
        elif evidence:
            verdict = Verdict.PARTIAL
        else:
            verdict = Verdict.UNCLEAR

        return VerificationResult(
            requirement_id=req.id,
            requirement_text=req.text,
            verdict=verdict,
            reasoning_steps=[
                "LLM structured output unavailable — used retrieval context only.",
                "Configure Ollama or Anthropic API for full chain-of-thought verification.",
            ],
            evidence=evidence,
            confidence=Confidence.LOW if verdict == Verdict.UNCLEAR else Confidence.MEDIUM,
            caveats="Fallback verification path",
        )

