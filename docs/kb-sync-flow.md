# Knowledge base sync flow

## Prerequisites

- RunPod pod with CUDA PyTorch image, ≥40 GB disk
- RunPod API key and SSH access configured in app Settings
- Local Ollama optional (only for verification, not sync)

## Steps (UI or `make sync-kb`)

| Step | Remote action |
|------|----------------|
| Bootstrap | `runpod/bootstrap.sh` — venv, torch CUDA check |
| Clone sync tool | pip install `cortex-docs-sync` |
| Sync docs | `cortex-docs-sync --output-dir /workspace/cortex_docs` |
| Chunk | `pipeline/chunk_html.py` |
| Embed | `pipeline/embed_gpu.py` (BGE-M3 FP16) |
| Index | `pipeline/build_index.py` (LanceDB) |
| Export | `pipeline/export_snapshot.py` → `.tar.zst` |
| Download | SCP to `~/.siwz-rag-lite/kb-staging/` |
| Swap | Validate `manifest.json`, rename to `kb-active` |

## Incremental mode

`cortex-docs-sync` maintains `.cortex_docs_state.json`. Unchanged publications are skipped unless **Full rebuild** is selected.

## Security

- API keys stored in OS keychain (`siwz-rag-lite` service)
- Never commit secrets; use `.env.example` for non-secret defaults only
