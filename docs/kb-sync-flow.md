# Knowledge base sync flow

## Prerequisites

- RunPod pod with CUDA PyTorch image, ≥40 GB disk
- RunPod API key and SSH access configured in app Settings
- Local Ollama optional (only for verification, not sync)

## Steps (UI or `make sync-kb` dry-run)

| Step | Action |
|------|--------|
| Bootstrap | Upload `runpod/` + `bootstrap.sh` (CUDA, venv, deps) |
| Pipeline | `pipeline/run_all.sh` — sync → chunk → embed → index → export |
| Download | SFTP `kb_snapshot.tar.zst` → `kb-staging/` |
| Swap | Extract, validate manifest, atomic rename to `kb-active` |

**Dry run** (UI checkbox or `make sync-kb`): builds local seed KB without RunPod.

**Test connection**: `POST /api/kb/test-connection` — SSH + `nvidia-smi`, or dry-run seed build.

## Incremental mode

`cortex-docs-sync` maintains `.cortex_docs_state.json`. Unchanged publications are skipped unless **Full rebuild** is selected.

## Security

- API keys stored in OS keychain (`siwz-rag-lite` service)
- Never commit secrets; use `.env.example` for non-secret defaults only
