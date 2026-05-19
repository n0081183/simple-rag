"""Atomic swap of knowledge base snapshot (staging → active)."""

from __future__ import annotations

import shutil
from pathlib import Path

from app.core.kb.manifest import KBManifest, load_manifest
from app.config import get_settings


def validate_staging(staging_path: Path) -> KBManifest:
    manifest_path = staging_path / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Staging KB missing manifest.json")
    manifest = load_manifest(manifest_path)
    lance = staging_path / "lance"
    if not lance.is_dir():
        raise ValueError("Staging KB missing lance/ directory")
    return manifest


def atomic_swap(staging_path: Path | None = None) -> KBManifest:
    settings = get_settings()
    staging = staging_path or settings.kb_staging_path
    active = settings.kb_active_path
    previous = settings.kb_previous_path

    manifest = validate_staging(staging)

    if active.exists():
        if previous.exists():
            shutil.rmtree(previous)
        active.rename(previous)

    staging.rename(active)
    settings.kb_staging_path.mkdir(parents=True, exist_ok=True)
    return manifest
