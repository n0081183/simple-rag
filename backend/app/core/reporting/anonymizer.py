"""Neutralize vendor/product names in reports (optional OPZ output)."""

from __future__ import annotations

from app.core.verification.schemas import VerificationResult

_REPLACEMENTS = [
    ("Palo Alto Networks", "dostawca"),
    ("Palo Alto", "dostawca"),
    ("Cortex XDR", "rozwiązanie EDR/XDR"),
    ("Cortex XSIAM", "rozwiązanie SIEM/SOAR"),
    ("Cortex XSOAR", "rozwiązanie SOAR"),
    ("Cortex XPANSE", "rozwiązanie ASM"),
    ("Cortex Xpanse", "rozwiązanie ASM"),
    ("Cortex Cloud", "rozwiązanie bezpieczeństwa chmury"),
    ("Cortex AgentiX", "rozwiązanie AI SecOps"),
    ("Cortex", "rozwiązanie"),
    ("XDR", "EDR/XDR"),
    ("XSIAM", "platforma SOC"),
    ("XSOAR", "SOAR"),
    ("XPANSE", "ASM"),
]


def anonymize_text(text: str) -> str:
    out = text
    for old, new in _REPLACEMENTS:
        out = out.replace(old, new)
    return out


def anonymize_results(results: list[VerificationResult]) -> list[VerificationResult]:
    out: list[VerificationResult] = []
    for r in results:
        copy = r.model_copy(deep=True)
        copy.requirement_text = anonymize_text(copy.requirement_text)
        copy.reasoning_steps = [anonymize_text(s) for s in copy.reasoning_steps]
        if copy.caveats:
            copy.caveats = anonymize_text(copy.caveats)
        for ev in copy.evidence:
            ev.quote = anonymize_text(ev.quote)
        out.append(copy)
    return out
