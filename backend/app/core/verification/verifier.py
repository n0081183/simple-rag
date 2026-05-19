"""Per-requirement verification orchestration."""

from __future__ import annotations

from app.config import get_settings
from app.core.extraction.schemas import ExtractedRequirement
from app.core.retrieval.retriever import Retriever, build_context
from app.core.verification.prompts import build_verify_system_prompt, build_verify_user_prompt
from app.core.verification.schemas import (
    Confidence,
    EvidenceItem,
    VerificationResult,
    Verdict,
)
from app.core.verification.llm_local import OllamaProvider
from app.core.verification.llm_api import AnthropicProvider


class VerificationOrchestrator:
    def __init__(self, product: str, language: str = "pl", anonymize: bool = False):
        self.product = product
        self.language = language
        self.anonymize = anonymize
        self.retriever = Retriever()
        settings = get_settings()
        if settings.llm_provider == "anthropic":
            try:
                self.llm = AnthropicProvider()
            except ValueError:
                self.llm = OllamaProvider()
        else:
            self.llm = OllamaProvider()

    def verify_one(self, req: ExtractedRequirement) -> VerificationResult:
        chunks = self.retriever.retrieve(req.text, product_filter=self.product)
        context = build_context(chunks)
        system = build_verify_system_prompt(self.product, self.language)
        user = build_verify_user_prompt(req.text, context, self.language)

        data = self.llm.complete_json(system, user)
        if data:
            try:
                result = VerificationResult(
                    requirement_id=req.id,
                    requirement_text=req.text,
                    **{k: v for k, v in data.items() if k not in ("requirement_id", "requirement_text")},
                )
                if not result.evidence and result.verdict != Verdict.UNCLEAR:
                    result.verdict = Verdict.UNCLEAR
                    result.confidence = Confidence.LOW
                return result
            except Exception:
                pass

        return self._mock_verify(req, chunks)

    def verify_all(self, requirements: list[ExtractedRequirement]) -> list[VerificationResult]:
        return [self.verify_one(r) for r in requirements if r.enabled]

    def _mock_verify(self, req: ExtractedRequirement, chunks) -> VerificationResult:
        evidence = [
            EvidenceItem(
                source_file=c.source_file,
                topic_url=c.topic_url,
                quote=c.text[:300],
                relevance="medium",
            )
            for c in chunks[:2]
        ]
        verdict = Verdict.UNCLEAR if not evidence else Verdict.PARTIAL
        return VerificationResult(
            requirement_id=req.id,
            requirement_text=req.text,
            verdict=verdict,
            reasoning_steps=[
                "Mock: Ollama unavailable or KB empty.",
                "Configure Ollama and build knowledge base.",
            ],
            evidence=evidence,
            confidence=Confidence.LOW,
            caveats="Milestone 0 mock response",
        )
