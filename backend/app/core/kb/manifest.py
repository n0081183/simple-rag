"""Knowledge base manifest schema and loader."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class ProductStats(BaseModel):
    chunk_count: int = 0
    source_hash: str | None = None


class KBManifest(BaseModel):
    version: str = "1"
    build_date: str
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    schema_version: str = "1"
    products: dict[str, ProductStats] = Field(default_factory=dict)
    total_chunks: int = 0


def load_manifest(path: Path) -> KBManifest:
    data = json.loads(path.read_text(encoding="utf-8"))
    return KBManifest.model_validate(data)


def save_manifest(path: Path, manifest: KBManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
