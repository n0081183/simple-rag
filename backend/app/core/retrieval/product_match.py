"""Auto-detect Cortex product — lexical + semantic (product capsules)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import BaseModel

from app.config import get_settings

_LEXICAL_SIGNALS: dict[str, list[str]] = {
    "xdr": ["edr", "xdr", "endpoint", "agent", "traps", "wildfire", "ngfw"],
    "xsiam": ["siem", "xsiam", "data lake", "broker", "soc", "siem"],
    "xsoar": ["soar", "xsoar", "playbook", "demisto", "war room"],
    "xpanse": ["xpanse", "asm", "attack surface", "zewnętrzna powierzchnia", "zewnętrznej"],
    "cortex_cloud": ["cnapp", "cspm", "cwpp", "prisma", "cortex cloud", "chmura", "cloud security"],
    "agentix": ["agentix", "agent ai", "agenti x", "copilot"],
}


class ProductSuggestion(BaseModel):
    product: str
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0


def _load_capsules() -> dict[str, str]:
    settings = get_settings()
    path = settings.kb_active_path / "product_capsules.json"
    if path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {k.lower(): v for k, v in raw.items()}
    return {k: " ".join(v) for k, v in _LEXICAL_SIGNALS.items()}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _lexical_scores(corpus_lower: str) -> dict[str, float]:
    scores: dict[str, float] = {}
    for product, keywords in _LEXICAL_SIGNALS.items():
        hits = sum(1 for kw in keywords if kw in corpus_lower)
        if hits:
            scores[product] = hits / len(keywords)
    return scores


def _semantic_scores(corpus: str, capsules: dict[str, str]) -> dict[str, float]:
    import os

    if os.environ.get("SIWZ_SKIP_ML"):
        return {}
    try:
        from app.core.retrieval.embedder import Embedder

        embedder = Embedder.get()
        corpus_emb = embedder.embed(corpus[:8000]).dense
        out: dict[str, float] = {}
        for product, text in capsules.items():
            if not text.strip():
                continue
            cap_emb = embedder.embed(text[:3000]).dense
            if corpus_emb and cap_emb and len(corpus_emb) == len(cap_emb):
                out[product] = _cosine(corpus_emb, cap_emb)
        return out
    except Exception:
        return {}


def detect_products(corpus: str, top_n: int = 3) -> list[ProductSuggestion]:
    """Rank products by combined lexical + semantic similarity to capsules."""
    if not corpus or not corpus.strip():
        return []

    corpus_lower = corpus.lower()
    capsules = _load_capsules()
    # Only score products present in KB capsules or known list
    products = set(_LEXICAL_SIGNALS) | set(capsules)

    lex = _lexical_scores(corpus_lower)
    sem = _semantic_scores(corpus, capsules)

    combined: list[ProductSuggestion] = []
    for product in products:
        ls = lex.get(product, 0.0)
        ss = sem.get(product, 0.0)
        # Weight semantic higher when available
        if sem:
            score = 0.35 * ls + 0.65 * ss
        else:
            score = ls
        if score > 0:
            combined.append(
                ProductSuggestion(
                    product=product,
                    score=round(score, 4),
                    lexical_score=round(ls, 4),
                    semantic_score=round(ss, 4),
                )
            )

    combined.sort(key=lambda x: x.score, reverse=True)
    return combined[:top_n]


def suggest_product(corpus: str) -> tuple[str | None, bool]:
    """Return (top_product, requires_expert_warning)."""
    ranked = detect_products(corpus, top_n=1)
    if not ranked:
        return None, True
    return ranked[0].product, True


def top_products(corpus: str, n: int = 3) -> list[tuple[str, float]]:
    return [(s.product, s.score) for s in detect_products(corpus, n)]
