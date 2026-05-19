#!/usr/bin/env python3
"""Build seed LanceDB knowledge base for local development."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings
from app.core.kb.ingest import build_seed_kb


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, help="KB directory (default: kb-active)")
    p.add_argument("--skip-ml", action="store_true", help="Mock embeddings (CI)")
    args = p.parse_args()

    path = args.output or get_settings().kb_active_path
    manifest = build_seed_kb(path, skip_ml=args.skip_ml)
    print(f"Built seed KB at {path}")
    print(f"  chunks: {manifest.total_chunks}")
    print(f"  products: {list(manifest.products.keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
