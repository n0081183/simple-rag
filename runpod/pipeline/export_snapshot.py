#!/usr/bin/env python3
"""Export portable KB snapshot as .tar.zst."""

import argparse
import json
import subprocess
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="/workspace/kb_build")
    p.add_argument("--output", default="/workspace/kb_snapshot.tar.zst")
    args = p.parse_args()

    src = Path(args.input_dir)
    out = Path(args.output)
    manifest = src / "manifest.json"
    lance = src / "lance"
    if not manifest.is_file() or not lance.is_dir():
        raise SystemExit(f"Missing build artifacts in {src}")

    # Optional sample for debug
    sample_path = src / "chunks_sample.jsonl"
    emb = Path("/workspace/embeddings.jsonl")
    if emb.is_file() and not sample_path.is_file():
        lines = emb.read_text(encoding="utf-8").splitlines()[:50]
        sample_path.write_text("\n".join(lines), encoding="utf-8")

    cmd = [
        "tar",
        "-I",
        "zstd -T0 -3",
        "-cf",
        str(out),
        "-C",
        str(src),
        "manifest.json",
        "product_capsules.json",
        "lance",
    ]
    if sample_path.is_file():
        cmd.append("chunks_sample.jsonl")

    subprocess.run(cmd, check=True)
    size_mb = out.stat().st_size / (1024 * 1024)
    meta = json.loads(manifest.read_text(encoding="utf-8"))
    print(f"[export] {out} ({size_mb:.1f} MB, {meta.get('total_chunks', '?')} chunks)")


if __name__ == "__main__":
    main()
