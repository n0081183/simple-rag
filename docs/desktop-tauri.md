# Desktop packaging (Tauri) — optional

SIWZ-RAG Lite ships primarily as a **local web app** (`make run` → http://localhost:8000). For a native desktop shell, use [Tauri 2](https://v2.tauri.app/) to wrap the FastAPI backend and static Next.js export.

## Prerequisites

- Rust toolchain (`rustup`)
- Tauri CLI: `cargo install tauri-cli`
- Same runtime as web: Python 3.11+ (uv), Ollama optional

## Layout

```
desktop/
  README.md           # Quick start for maintainers
  src-tauri/          # Created by `tauri init` (not committed until you run init)
```

## Recommended flow

1. Build the web assets:

   ```bash
   make install
   make build
   ```

2. Initialize Tauri (once):

   ```bash
   cd desktop
   cargo tauri init
   ```

3. Configure `tauri.conf.json` to:
   - **beforeDevCommand**: `make dev` or run uvicorn + next dev separately
   - **beforeBuildCommand**: `make build` from repo root
   - **distDir**: `../frontend/out`
   - **devUrl** / **frontendDist**: point to `http://127.0.0.1:8000` in production the sidecar runs uvicorn

4. **Sidecar pattern**: bundle `uv` + project venv and start:

   ```bash
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   from `backend/` with `cwd` set to the app data directory (`~/.siwz-rag-lite`).

5. Ship secrets via OS keychain (unchanged); never embed API keys in the `.app` / `.msi`.

## Scope note

M4 documents the path; full Tauri CI artifacts are left to release engineering. The Playwright suite (`make e2e`) validates the same UI served by FastAPI static export.
