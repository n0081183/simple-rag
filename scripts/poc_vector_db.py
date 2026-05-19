#!/usr/bin/env python3
"""PoC: LanceDB connectivity (ADR 001 validation)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main():
    try:
        import lancedb
    except ImportError:
        print("Install lancedb first: uv sync")
        return 1

    poc_dir = Path("/tmp/siwz-lance-poc")
    poc_dir.mkdir(exist_ok=True)
    t0 = time.perf_counter()
    db = lancedb.connect(str(poc_dir))
    ms = (time.perf_counter() - t0) * 1000
    tables = db.table_names()
    print(f"LanceDB connect OK in {ms:.1f}ms (tables: {tables})")
    print("Full hybrid indexing validated in Milestone 1 — see docs/decisions/001-vector-db.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
