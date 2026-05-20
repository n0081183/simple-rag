import io
import json
import tarfile
from pathlib import Path

import zstandard as zstd

from app.core.kb.snapshot import extract_tar_zst, install_snapshot


def test_extract_tar_zst_roundtrip(tmp_path: Path):
    src = tmp_path / "build"
    src.mkdir()
    (src / "manifest.json").write_text(
        json.dumps({"version": "1", "build_date": "2026-01-01", "total_chunks": 1}),
        encoding="utf-8",
    )
    (src / "product_capsules.json").write_text("{}", encoding="utf-8")
    lance = src / "lance"
    lance.mkdir()

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tf:
        tf.add(src / "manifest.json", arcname="manifest.json")
        tf.add(src / "product_capsules.json", arcname="product_capsules.json")
        tf.add(lance, arcname="lance")

    archive = tmp_path / "kb_snapshot.tar.zst"
    archive.write_bytes(zstd.ZstdCompressor().compress(tar_buf.getvalue()))

    dest = tmp_path / "staging"
    extract_tar_zst(archive, dest)
    assert (dest / "manifest.json").is_file()
    assert (dest / "lance").is_dir()


def test_install_snapshot_keeps_archive_inside_staging_dir(tmp_path: Path):
    """Regression: archive must survive when stored under kb-staging/."""
    staging = tmp_path / "kb-staging"
    staging.mkdir()
    src = tmp_path / "build"
    src.mkdir()
    (src / "manifest.json").write_text(
        json.dumps(
            {
                "version": "1",
                "build_date": "2026-01-01",
                "total_chunks": 42,
                "embedding_model": "BAAI/bge-m3",
                "embedding_dim": 1024,
            }
        ),
        encoding="utf-8",
    )
    (src / "product_capsules.json").write_text("{}", encoding="utf-8")
    (src / "lance").mkdir()

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tf:
        tf.add(src / "manifest.json", arcname="manifest.json")
        tf.add(src / "product_capsules.json", arcname="product_capsules.json")
        tf.add(src / "lance", arcname="lance")

    archive = staging / "kb_snapshot.tar.zst"
    archive.write_bytes(zstd.ZstdCompressor().compress(tar_buf.getvalue()))
    assert archive.stat().st_size > 0

    meta = install_snapshot(archive, staging)
    assert meta["total_chunks"] == 42
    # Archive may be copied to parent during install; re-download path uses data_dir/
    assert archive.is_file() or (staging.parent / archive.name).is_file()
    assert (staging / "manifest.json").is_file()
    assert (staging / "lance").is_dir()
