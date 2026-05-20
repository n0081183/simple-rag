# SIWZ-RAG Lite

Professional tool for verifying public procurement requirements (SIWZ/RFP) against **Palo Alto Cortex** documentation.

[Polska wersja](README.md)

## Features

| Function | Description |
|----------|-------------|
| **A — Verification** | PDF/DOCX or pasted text → requirement extraction → RAG + LLM → cited report |
| **B — KB sync** | RunPod GPU → `cortex-docs-sync` → embeddings → portable LanceDB snapshot |

## Quick start (~10 min)

```bash
git clone https://github.com/n0081183/simple-rag.git siwz-rag-lite
cd siwz-rag-lite
make install
ollama pull qwen3:8b
make run    # http://localhost:8000
```

Requirements: Python 3.11+, Node 20+, [Ollama](https://ollama.com).

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/decisions/](docs/decisions/).

## Makefile commands

| Command | Description |
|---------|-------------|
| `make install` | Dependencies + UI build |
| `make dev` | Dev servers |
| `make run` | Production server |
| `make eval` | Gold-set evaluation |
| `make sync-kb` | KB sync CLI |
| `make preflight` | Environment check |

## Security

RunPod and LLM API keys are stored in the **OS keychain** only — never in the repository.

## Status

- [x] M0: Skeleton, ADR, CI
- [x] M1: LLM extraction, RAG, verification, MD report, gold set
- [x] M2: RunPod SSH pipeline, snapshot, atomic swap
- [x] M3: DOCX/XLSX exports, product auto-detect (top 3 + confirm), LLM toggle, report anonymization
- [ ] M4: Playwright E2E, Tauri (optional)

## License

MIT — see [LICENSE](LICENSE).
