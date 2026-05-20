import io
import json
import tarfile
from pathlib import Path

import zstandard as zstd

from app.core.kb.snapshot import extract_tar_zst


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
