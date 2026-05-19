"""Multi-query retrieval with OS sub-query decomposition and RRF hybrid fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import get_settings
from app.core.domain_knowledge.synonyms import expand_query
from app.core.kb.store import KnowledgeStore, SearchResult
from app.core.retrieval.embedder import Embedder
from app.core.retrieval.reranker import Reranker


_OS_GROUPS: dict[str, re.Pattern] = {
    "windows": re.compile(r"\b(windows\s*(?:10|11|server)?|win\s*\d+)\b", re.I),
    "linux_rhel": re.compile(r"\b(rhel|red\s*hat|centos)\s*[\d\.]*\b", re.I),
    "linux_ubuntu": re.compile(r"\bubuntu\s*[\d\.]*\b", re.I),
    "macos": re.compile(r"\b(macos|mac\s*os|osx)\b", re.I),
    "mobile": re.compile(r"\b(android|ios|iphone|ipad)\b", re.I),
}


@dataclass
class RetrievedChunk:
    id: str
    text: str
    score: float
    source_file: str
    topic_url: str
    product: str
    metadata: dict


def _detect_os_sub_queries(query: str) -> list[str]:
    matched = [name for name, pat in _OS_GROUPS.items() if pat.search(query)]
    if len(matched) < 2:
        return []
    sub_queries = []
    for name in matched:
        sub_queries.append(f"{query} {name} compatibility support matrix")
    return sub_queries


def _rrf_merge(result_lists: list[list[SearchResult]], k: int = 60) -> list[SearchResult]:
    scores: dict[str, float] = {}
    items: dict[str, SearchResult] = {}
    for results in result_lists:
        for rank, r in enumerate(results):
            scores[r.id] = scores.get(r.id, 0.0) + 1.0 / (k + rank + 1)
            items[r.id] = r
    merged = sorted(items.values(), key=lambda r: scores[r.id], reverse=True)
    for r in merged:
        r.score = scores[r.id]
    return merged


class Retriever:
    def __init__(self, store: KnowledgeStore | None = None):
        settings = get_settings()
        self.store = store or KnowledgeStore(settings.kb_active_path)
        self.embedder = Embedder.get()
        self.reranker = Reranker.get()
        self.top_k = settings.retrieval_top_k
        self.top_n = settings.retrieval_top_n

    def retrieve(self, query: str, product_filter: str | None = None) -> list[RetrievedChunk]:
        emb = self.embedder.embed(query)
        lists: list[list[SearchResult]] = [
            self.store.hybrid_search(
                dense=emb.dense,
                sparse_indices=emb.sparse_indices,
                sparse_values=emb.sparse_values,
                query_text=query,
                product=product_filter,
                limit=self.top_k,
            )
        ]

        for sub_q in _detect_os_sub_queries(query):
            sub_emb = self.embedder.embed(sub_q)
            lists.append(
                self.store.hybrid_search(
                    dense=sub_emb.dense,
                    sparse_indices=sub_emb.sparse_indices,
                    sparse_values=sub_emb.sparse_values,
                    query_text=sub_q,
                    product=product_filter,
                    limit=4,
                )
            )

        for term in expand_query(query, max_expansions=3):
            expanded = f"{query} {term}"
            exp_emb = self.embedder.embed(expanded)
            lists.append(
                self.store.hybrid_search(
                    dense=exp_emb.dense,
                    sparse_indices=exp_emb.sparse_indices,
                    sparse_values=exp_emb.sparse_values,
                    query_text=expanded,
                    product=product_filter,
                    limit=3,
                )
            )

        merged = _rrf_merge(lists)[: self.top_k]
        passages = [m.text for m in merged]
        ranked = self.reranker.rerank(query, passages, top_n=self.top_n)

        out: list[RetrievedChunk] = []
        for idx, score in ranked:
            m = merged[idx]
            out.append(
                RetrievedChunk(
                    id=m.id,
                    text=m.text,
                    score=score,
                    source_file=m.source_file,
                    topic_url=m.topic_url,
                    product=m.product,
                    metadata=m.metadata,
                )
            )
        return out


def build_context(chunks: list[RetrievedChunk], max_chars: int = 14000) -> str:
    parts = []
    total = 0
    for i, c in enumerate(chunks, 1):
        block = (
            f"--- Chunk {i} (score={c.score:.3f}) ---\n"
            f"Product: {c.product}\n"
            f"Source: {c.source_file}\n"
            f"URL: {c.topic_url}\n\n"
            f"{c.text}\n"
        )
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts)
