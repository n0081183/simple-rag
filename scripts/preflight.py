#!/usr/bin/env python3
"""Environment preflight checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx
from app.config import get_settings


def main() -> int:
    settings = get_settings()
    ok = True
    print(f"Data dir: {settings.data_dir}")
    print(f"KB active: {settings.kb_active_path} (exists={settings.kb_active_path.exists()})")

    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=5.0)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"Ollama: OK — models: {', '.join(models[:5]) or '(none)'}")
            if settings.ollama_model not in " ".join(models):
                print(f"  WARN: {settings.ollama_model} not in list — run: ollama pull {settings.ollama_model}")
        else:
            print(f"Ollama: HTTP {r.status_code}")
            ok = False
    except Exception as e:
        print(f"Ollama: unreachable ({e})")
        ok = False

    try:
        import lancedb  # noqa: F401

        print("LanceDB: OK")
    except ImportError:
        print("LanceDB: not installed")
        ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
