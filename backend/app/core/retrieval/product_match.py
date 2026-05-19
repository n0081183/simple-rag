"""Auto-detect Cortex product from requirements text (lexical + semantic)."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings

_LEXICAL_SIGNALS: dict[str, list[str]] = {
    "xdr": ["edr", "xdr", "endpoint", "agent", "traps", "wildfire"],
    "xsiam": ["siem", "xsiam", "data lake", "broker", "soc"],
    "xsoar": ["soar", "xsoar", "playbook", "demisto", "war room"],
    "xpanse": ["xpanse", "asm", "attack surface", "zewnętrzna powierzchnia"],
    "cortex_cloud": ["cnapp", "cspm", "cwpp", "prisma", "cortex cloud", "chmura"],
    "agentix": ["agentix", "agent ai", "agenti x"],
}


def _load_capsules() -> dict[str, str]:
    settings = get_settings()
    path = settings.kb_active_path / "product_capsules.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {k: " ".join(v) for k, v in _LEXICAL_SIGNALS.items()}


def suggest_product(corpus: str) -> tuple[str | None, bool]:
    """Return (top_product, requires_expert_warning)."""
    corpus_lower = corpus.lower()
    scores: dict[str, float] = {}

    for product, keywords in _LEXICAL_SIGNALS.items():
        score = sum(1 for kw in keywords if kw in corpus_lower)
        if score:
            scores[product] = float(score)

    if not scores:
        return None, True

    top = max(scores, key=scores.get)  # type: ignore[arg-type]
    # Always warn on auto-detect per spec
    return top, True


def top_products(corpus: str, n: int = 3) -> list[tuple[str, float]]:
    corpus_lower = corpus.lower()
    scores = {
        product: sum(1 for kw in kws if kw in corpus_lower) / max(len(kws), 1)
        for product, kws in _LEXICAL_SIGNALS.items()
    }
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(p, s) for p, s in ranked[:n] if s > 0]
