"""Cross-encoder reranker (BAAI/bge-reranker-v2-m3)."""

from __future__ import annotations

from app.config import get_settings


class Reranker:
    _instance: Reranker | None = None

    def __init__(self):
        self._model = None
        settings = get_settings()
        self.model_name = settings.reranker_model

    @classmethod
    def get(cls) -> Reranker:
        if cls._instance is None:
            cls._instance = Reranker()
        return cls._instance

    def _load(self):
        if self._model is not None:
            return
        import os

        if os.environ.get("SIWZ_SKIP_ML"):
            self._model = None
            return
        try:
            from FlagEmbedding import FlagReranker

            self._model = FlagReranker(self.model_name, use_fp16=True)
        except Exception:
            self._model = None

    def rerank(self, query: str, passages: list[str], top_n: int = 8) -> list[tuple[int, float]]:
        if not passages:
            return []
        self._load()
        if self._model is None:
            return [(i, 1.0 - i * 0.01) for i in range(min(top_n, len(passages)))]
        pairs = [[query, p] for p in passages]
        try:
            scores = self._model.compute_score(pairs, normalize=True)
            if not isinstance(scores, list):
                scores = [scores]
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            return [(idx, float(score)) for idx, score in ranked[:top_n]]
        except Exception:
            return [(i, 1.0 - i * 0.01) for i in range(min(top_n, len(passages)))]
