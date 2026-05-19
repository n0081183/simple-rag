"""Cross-encoder reranker — sentence-transformers with FlagEmbedding fallback."""

from __future__ import annotations

import logging
import os

from app.config import get_settings

logger = logging.getLogger(__name__)


class Reranker:
    _instance: Reranker | None = None

    def __init__(self):
        self._st_model = None
        self._flag_model = None
        settings = get_settings()
        self.model_name = settings.reranker_model

    @classmethod
    def get(cls) -> Reranker:
        if cls._instance is None:
            cls._instance = Reranker()
        return cls._instance

    def _load(self):
        if self._st_model is not None or self._flag_model is not None:
            return
        if os.environ.get("SIWZ_SKIP_ML"):
            return
        try:
            from sentence_transformers import CrossEncoder

            self._st_model = CrossEncoder(self.model_name)
            return
        except Exception as e:
            logger.debug("cross_encoder_load_failed %s", e)
        try:
            from FlagEmbedding import FlagReranker

            self._flag_model = FlagReranker(self.model_name, use_fp16=True)
        except Exception as e:
            logger.debug("flag_reranker_load_failed %s", e)

    def rerank(self, query: str, passages: list[str], top_n: int = 8) -> list[tuple[int, float]]:
        if not passages:
            return []
        self._load()

        if self._st_model is not None:
            pairs = [[query, p] for p in passages]
            scores = self._st_model.predict(pairs)
            ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
            return [(idx, float(score)) for idx, score in ranked[:top_n]]

        if self._flag_model is not None:
            try:
                pairs = [[query, p] for p in passages]
                scores = self._flag_model.compute_score(pairs, normalize=True)
                if not isinstance(scores, list):
                    scores = [scores]
                ranked = sorted(enumerate(scores), key=lambda x: float(x[1]), reverse=True)
                return [(idx, float(score)) for idx, score in ranked[:top_n]]
            except Exception as e:
                logger.warning("rerank_failed %s", e)

        return [(i, 1.0 - i * 0.01) for i in range(min(top_n, len(passages)))]
