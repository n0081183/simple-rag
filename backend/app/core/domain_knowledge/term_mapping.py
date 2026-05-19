"""SIWZ term → product terminology mapping."""

from __future__ import annotations

TERM_MAPPING: dict[str, tuple[str, str, str]] = {
    # siwz_term: (product_term, desc_pl, desc_en)
    "agent endpointowy": ("Cortex XDR Agent", "Agent EDR na stacji roboczej", "Endpoint EDR agent"),
    "system soc": ("Cortex XSIAM", "Platforma SIEM/SOAR", "SIEM/SOAR platform"),
    "soar": ("Cortex XSOAR", "Automatyzacja SOAR", "SOAR automation"),
    "edr": ("Cortex XDR", "Wykrywanie i reakcja na endpointach", "Endpoint detection and response"),
    "xdr": ("Cortex XDR", "Extended Detection and Response", "Extended Detection and Response"),
    "siem": ("Cortex XSIAM", "Korelacja zdarzeń", "Event correlation"),
    "powierzchnia ataku": ("Cortex XPANSE", "Attack Surface Management", "Attack Surface Management"),
    "chmura publiczna": ("Cortex Cloud", "Bezpieczeństwo chmury", "Cloud security"),
}


def translate_term(term: str, language: str = "pl") -> str | None:
    entry = TERM_MAPPING.get(term.lower())
    if not entry:
        return None
    return entry[1] if language == "pl" else entry[2]


def get_relevant_terms_for_requirement(requirement: str) -> list[str]:
    req_lower = requirement.lower()
    hits = []
    for siwz_term, (product_term, _, _) in TERM_MAPPING.items():
        if siwz_term in req_lower:
            hits.append(f"{siwz_term} → {product_term}")
    return hits[:15]
