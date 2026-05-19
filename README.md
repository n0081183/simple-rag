# SIWZ-RAG Lite

Narzędzie do weryfikacji wymagań SIWZ/SWZ i budowy bazy wiedzy z dokumentacji **Palo Alto Cortex** (XDR, XSIAM, XSOAR, XPANSE, Cortex Cloud, AgentiX).

[English version](README.en.md)

## Funkcje

| Funkcja | Opis |
|---------|------|
| **A — Weryfikacja** | PDF/DOCX lub tekst → ekstrakcja wymagań → RAG + LLM → raport z cytatami |
| **B — Sync KB** | RunPod GPU → `cortex-docs-sync` → embedding → portable snapshot LanceDB |

## Szybki start (~10 min)

```bash
git clone https://github.com/n0081183/simple-rag.git siwz-rag-lite
cd siwz-rag-lite
make install    # uv + npm + build frontendu
ollama pull qwen3:8b
make run        # http://localhost:8000
```

Wymagania: Python 3.11+, Node 20+, [Ollama](https://ollama.com), opcjonalnie GPU do lokalnych embeddingów.

## Architektura

Zobacz [docs/architecture.md](docs/architecture.md) i ADR w [docs/decisions/](docs/decisions/).

```mermaid
flowchart LR
    UI[Next.js] --> API[FastAPI]
    API --> EXT[Ekstrakcja]
    API --> RAG[RAG + Reranker]
    RAG --> LDB[(LanceDB)]
    RunPod --> LDB
```

## Komendy Makefile

| Komenda | Opis |
|---------|------|
| `make install` | Zależności + build UI |
| `make dev` | Backend :8000 + frontend :3000 |
| `make run` | Produkcja (FastAPI + static) |
| `make eval` | Gold set 20 wymagań |
| `make sync-kb` | Sync bazy (CLI) |
| `make preflight` | Sprawdzenie Ollama / LanceDB |
| `make seed-kb` | Budowa seedowej bazy wiedzy (dev) |

## Bezpieczeństwo

Klucze RunPod i API LLM — **wyłącznie keychain OS** (`siwz-rag-lite`), nigdy w repo.

## Status (Milestone 0)

- [x] Szkielet repo, ADR, CI
- [x] Pipeline ekstrakcji (pre-split + mock validator)
- [x] Interfejsy RAG, weryfikacji, LanceDB
- [x] UI Next.js (verify + KB sync mock)
- [ ] Milestone 1: pełna ekstrakcja LLM, raporty, gold set
- [ ] Milestone 2: RunPod SSH pipeline

## Licencja

MIT — zobacz [LICENSE](LICENSE).
