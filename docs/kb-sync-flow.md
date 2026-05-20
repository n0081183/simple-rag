# Knowledge base sync flow

## Prerequisites

- RunPod pod with CUDA PyTorch image, ≥40 GB disk
- RunPod API key and SSH access configured in app Settings
- Local Ollama optional (only for verification, not sync)

## Steps (UI or `make sync-kb` dry-run)

| Step | Action |
|------|--------|
| Bootstrap | Upload `runpod/` + `bootstrap.sh` (CUDA, venv, **staged pip** + swap) |
| Pipeline | `pipeline/run_all.sh` — sync → chunk → embed → index → export |
| Download | SFTP → `~/.siwz-rag-lite/kb_snapshot.tar.zst` |
| Activate | `atomic_swap`: `kb-staging/` → `kb-active/` (app uses KB immediately) |
| Manual install | `POST /api/kb/install-from-archive` if archive already on disk |
| Swap | Extract, validate manifest, atomic rename to `kb-active` |

**Dry run** (UI checkbox or `make sync-kb`): builds local seed KB without RunPod.

### Bootstrap notes (RunPod)

- Dependencies install **one stage at a time** (~5–15 min first run) to avoid OOM (`Killed` during pip).
- An **8G swap file** is added automatically when system RAM &lt; 32GB.
- Re-runs skip bootstrap if `/workspace/.bootstrap_ok` exists (`FORCE_BOOTSTRAP=1` to reinstall).
- If pip fails, inspect `/workspace/bootstrap-pip.log` on the pod.

### Rate limiting (anti-bot / 429)

The portal returns **HTTP 429** when crawled too fast. SIWZ ships a patched `cortex-docs-sync` in `runpod/cortex_docs_sync_vendor/`:

| Setting | Default | Env override |
|---------|---------|--------------|
| Request rate | **1.0 req/s per thread** (UI on KB page) | `rate_limit_rps`; effective ≈ rate × workers |
| Topic download workers | **4** (default) | `topic_workers`; `CORTEX_SYNC_TOPIC_WORKERS` |
| Embed batch / logs | **96** batch, progress every **2000** chunks | `EMBED_BATCH_SIZE`, `EMBED_LOG_EVERY`; logs show `device=cuda` |

Embedding runs on **CUDA only** (`embed_gpu.py` aborts without GPU). SSH log UI filters tqdm `\r` bars; progress appears as `[embed] N/total (%)` lines.
| Partial failures | **continue pipeline** | default; `CORTEX_SYNC_STRICT=1` to fail |

Bootstrap always reinstalls the editable vendor package (even when `.bootstrap_ok` exists) so an old git install cannot shadow it.

After a failed run with `Failed: 1` in docs-sync, re-run sync only — incremental mode skips unchanged pubs; or delete state and refetch the missing title.

### Product scope

The UI sends all selected products as `--products xdr xsiam …` (single flag).  
Do not use repeated `--product` abbreviations on `sync_docs.py` — argparse would keep only the last one.

### Snapshot download (macOS)

Local extract uses the Python `zstandard` package (no Homebrew `zstd` required). Install deps: `uv sync`.

**Test connection**: `POST /api/kb/test-connection` — SSH + `nvidia-smi`, or dry-run seed build.

## Incremental mode

`cortex-docs-sync` maintains `.cortex_docs_state.json`. Unchanged publications are skipped unless **Full rebuild** is selected.

## Security

- API keys stored in OS keychain (`siwz-rag-lite` service)
- Never commit secrets; use `.env.example` for non-secret defaults only
