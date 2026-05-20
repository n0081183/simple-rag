"""Download and extract portable KB snapshots."""

from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
from pathlib import Path

from app.core.kb.manifest import load_manifest
from app.core.kb.swap import validate_staging


def extract_tar_zst(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zst" or str(archive).endswith(".tar.zst"):
        subprocess.run(
            ["tar", "--use-compress-program=zstd", "-xf", str(archive), "-C", str(dest)],
            check=True,
        )
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            tf.extractall(dest)
    else:
        raise ValueError(f"Unsupported archive: {archive}")


def install_snapshot(archive: Path, staging_path: Path) -> dict:
    if staging_path.exists():
        shutil.rmtree(staging_path)
    staging_path.mkdir(parents=True)
    extract_tar_zst(archive, staging_path)
    manifest = validate_staging(staging_path)
    return json.loads((staging_path / "manifest.json").read_text(encoding="utf-8"))
