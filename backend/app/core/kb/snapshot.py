"""Download and extract portable KB snapshots."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from app.core.kb.swap import validate_staging


def _tar_extractall(tf: tarfile.TarFile, dest: Path) -> None:
    if sys.version_info >= (3, 12):
        tf.extractall(path=dest, filter="data")
    else:
        tf.extractall(path=dest)


def _extract_tar_zst_python(archive: Path, dest: Path) -> None:
    import io

    import zstandard as zstd

    dest.mkdir(parents=True, exist_ok=True)
    raw = zstd.ZstdDecompressor().decompress(archive.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        _tar_extractall(tf, dest)


def _extract_tar_zst_cli(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["tar", "--use-compress-program=zstd", "-xf", str(archive), "-C", str(dest)],
        check=True,
    )


def _extract_tar_zst_zstd_pipe(archive: Path, dest: Path) -> None:
    """Fallback when tar lacks --use-compress-program (BSD/macOS)."""
    dest.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        ["zstd", "-d", "-c", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert proc.stdout is not None
        with tarfile.open(fileobj=proc.stdout, mode="r|") as tf:
            _tar_extractall(tf, dest)
    finally:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"zstd decompress failed: {stderr}")


def extract_tar_zst(archive: Path, dest: Path) -> None:
    """Extract .tar.zst using Python (preferred) or system tools."""
    if not (archive.suffix == ".zst" or str(archive).endswith(".tar.zst")):
        if tarfile.is_tarfile(archive):
            with tarfile.open(archive) as tf:
                _tar_extractall(tf, dest)
            return
        raise ValueError(f"Unsupported archive: {archive}")

    errors: list[str] = []
    for fn in (_extract_tar_zst_python, _extract_tar_zst_zstd_pipe, _extract_tar_zst_cli):
        try:
            if dest.exists():
                shutil.rmtree(dest)
            fn(archive, dest)
            return
        except Exception as e:
            errors.append(f"{fn.__name__}: {e}")
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)

    raise RuntimeError("Failed to extract snapshot:\n" + "\n".join(errors))


def install_snapshot(archive: Path, staging_path: Path) -> dict:
    if staging_path.exists():
        shutil.rmtree(staging_path)
    staging_path.mkdir(parents=True)
    extract_tar_zst(archive, staging_path)
    manifest = validate_staging(staging_path)
    return json.loads((staging_path / "manifest.json").read_text(encoding="utf-8"))
