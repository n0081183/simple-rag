"""Chain-of-thought verification prompts (4 steps)."""

from __future__ import annotations

from app.core.domain_knowledge.product_facts import get_domain_knowledge_prompt
from app.core.domain_knowledge.term_mapping import get_relevant_terms_for_requirement


SYSTEM_VERIFY_PL = """Jesteś ekspertem Palo Alto Networks Cortex weryfikującym wymagania SIWZ.
ZASADY:
- Jeśli brak dowodu w kontekście → werdykt UNCLEAR, nie zgaduj.
- Zawsze cytuj fragmenty dokumentacji w polu evidence.
- Pewność LOW → preferuj UNCLEAR zamiast MET.

Kroki rozumowania (reasoning_steps):
1) Rozłóż pojęcia w wymaganiu (wersje OS, liczby, modalność).
2) Zmapuj terminologię SIWZ na terminologię produktu.
3) Porównaj z kontekstem dokumentacji — cytaty obowiązkowe.
4) Wydaj werdykt i confidence."""

SYSTEM_VERIFY_EN = """You are a Palo Alto Networks Cortex expert verifying RFP requirements.
RULES:
- No evidence in context → verdict UNCLEAR, do not guess.
- Always quote documentation fragments in evidence.
- LOW confidence → prefer UNCLEAR over MET.

Reasoning steps (reasoning_steps):
1) Decompose requirement concepts (OS versions, counts, modality).
2) Map RFP terminology to product terminology.
3) Compare with documentation context — quotes mandatory.
4) Issue verdict and confidence."""


def build_verify_system_prompt(product: str, language: str) -> str:
    base = SYSTEM_VERIFY_PL if language == "pl" else SYSTEM_VERIFY_EN
    domain = get_domain_knowledge_prompt(product, language)
    return f"{base}\n\n{domain}" if domain else base


def build_verify_user_prompt(requirement: str, context: str, language: str) -> str:
    terms = get_relevant_terms_for_requirement(requirement)
    terms_block = "\n".join(terms) if terms else "(brak)" if language == "pl" else "(none)"
    header = "KONTEKST DOKUMENTACJI" if language == "pl" else "DOCUMENTATION CONTEXT"
    return (
        f"=== {header} START ===\n{context}\n=== {header} END ===\n\n"
        f"WYMAGANIE:\n{requirement}\n\n"
        f"MAPOWANIE TERMINÓW:\n{terms_block}\n\n"
        "Odpowiedz wyłącznie jako JSON zgodny ze schematem VerificationResult."
    )
