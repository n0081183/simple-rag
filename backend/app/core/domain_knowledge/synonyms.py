"""Synonym expansion for retrieval query enhancement."""

from __future__ import annotations

SYNONYMS: dict[str, list[str]] = {
    "Cortex XDR Agent": [
        "agent endpointowy",
        "agent EDR",
        "endpoint agent",
        "traps agent",
    ],
    "Cortex XDR": ["xdr", "edr", "extended detection and response"],
    "Cortex XSIAM": ["xsiam", "siem", "data lake", "broker vm"],
    "Cortex XSOAR": ["xsoar", "soar", "playbook", "demisto"],
    "Cortex XPANSE": ["xpanse", "asm", "attack surface"],
    "Cortex Cloud": ["cortex cloud", "cnapp", "cspm", "prisma cloud"],
    "Cortex AgentiX": ["agentix", "ai agent", "agent ai"],
}


def expand_query(query: str, max_expansions: int = 6) -> list[str]:
    """Return additional query terms from domain synonyms."""
    query_lower = query.lower()
    expansions: list[str] = []
    seen: set[str] = set()

    for canonical, variants in SYNONYMS.items():
        if canonical.lower() in query_lower:
            for v in variants:
                if v.lower() not in seen and v.lower() not in query_lower:
                    seen.add(v.lower())
                    expansions.append(v)
        else:
            for v in variants:
                if v.lower() in query_lower and canonical.lower() not in seen:
                    seen.add(canonical.lower())
                    expansions.append(canonical)
                    break

        if len(expansions) >= max_expansions:
            break

    return expansions[:max_expansions]
