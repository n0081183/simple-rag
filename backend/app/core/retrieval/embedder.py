"""BGE-M3 embedder wrapper (dense + sparse) — lazy load."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings


@dataclass
class EmbeddingResult:
    dense: list[float]
    sparse_indices: list[int]
    sparse_values: list[float]


class Embedder:
    _instance: Embedder | None = None

    def __init__(self):
        self._model = None
        settings = get_settings()
        self.model_name = settings.embedding_model

    @classmethod
    def get(cls) -> Embedder:
        if cls._instance is None:
            cls._instance = Embedder()
        return cls._instance

    def _load(self):
        if self._model is not None:
            return
        import os

        if os.environ.get("SIWZ_SKIP_ML"):
            self._model = None
            return
        try:
            from FlagEmbedding import BGEM3FlagModel

            self._model = BGEM3FlagModel(self.model_name, use_fp16=True)
        except Exception:
            self._model = None

    def embed(self, text: str) -> EmbeddingResult:
        self._load()
        if self._model is None:
            # Mock embedding for CI / no-GPU dev
            return EmbeddingResult(dense=[0.0] * 1024, sparse_indices=[], sparse_values=[])
        out = self._model.encode([text], return_dense=True, return_sparse=True)
        dense = out["dense_vecs"][0].tolist()
        lexical = out["lexical_weights"][0]
        indices = [int(k) for k in lexical.keys()]
        values = [float(v) for v in lexical.values()]
        return EmbeddingResult(dense=dense, sparse_indices=indices, sparse_values=values)
