"""LanceDB knowledge store (ADR 001)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings


@dataclass
class SearchResult:
    id: str
    text: str
    score: float
    source_file: str = ""
    topic_url: str = ""
    product: str = ""
    metadata: dict = field(default_factory=dict)


class KnowledgeStore:
    TABLE_NAME = "chunks"

    def __init__(self, kb_path: Path | None = None):
        settings = get_settings()
        self.kb_path = kb_path or settings.kb_active_path
        self._db = None
        self._table = None

    def _ensure_db(self):
        if self._db is not None:
            return
        try:
            import lancedb

            self.kb_path.mkdir(parents=True, exist_ok=True)
            self._db = lancedb.connect(str(self.kb_path / "lance"))
            if self.TABLE_NAME in self._db.table_names():
                self._table = self._db.open_table(self.TABLE_NAME)
        except ImportError:
            self._db = None

    def is_loaded(self) -> bool:
        return (self.kb_path / "manifest.json").is_file()

    def list_products(self) -> list[tuple[str, int]]:
        manifest_path = self.kb_path / "manifest.json"
        if not manifest_path.is_file():
            return []
        from app.core.kb.manifest import load_manifest

        m = load_manifest(manifest_path)
        return [(p, s.chunk_count) for p, s in m.products.items()]

    def hybrid_search(
        self,
        dense: list[float],
        sparse_indices: list[int],
        sparse_values: list[float],
        query_text: str,
        product: str | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        self._ensure_db()
        if self._table is None:
            return self._mock_search(query_text, product, limit)

        # Vector search + optional FTS; filter by product in Python if needed
        try:
            results = (
                self._table.search(dense, vector_column_name="dense")
                .limit(limit * 2)
                .to_list()
            )
        except Exception:
            return self._mock_search(query_text, product, limit)

        out: list[SearchResult] = []
        for i, row in enumerate(results):
            if product and row.get("product") not in (product, "shared", None):
                if row.get("product", "").lower() != product.lower():
                    continue
            out.append(
                SearchResult(
                    id=str(row.get("id", i)),
                    text=row.get("text", ""),
                    score=float(row.get("_distance", 0) or 1.0 / (i + 1)),
                    source_file=row.get("source_file", ""),
                    topic_url=row.get("topic_url", ""),
                    product=row.get("product", ""),
                    metadata=json.loads(row.get("metadata", "{}") or "{}"),
                )
            )
            if len(out) >= limit:
                break
        return out

    def _mock_search(self, query_text: str, product: str | None, limit: int) -> list[SearchResult]:
        """Placeholder when KB not built — enables UI/API dev without index."""
        return [
            SearchResult(
                id=str(uuid.uuid4()),
                text=f"[Mock context] No knowledge base loaded. Query: {query_text[:80]}",
                score=0.5,
                source_file="mock.html",
                topic_url="https://docs-cortex.paloaltonetworks.com/",
                product=product or "xdr",
            )
        ][:limit]
