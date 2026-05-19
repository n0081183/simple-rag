# RunPod GPU pipeline

One-shot pod workflow for building the portable knowledge base snapshot.

## Manual pod setup

1. Create a RunPod pod: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
2. Disk ≥ 40 GB, GPU RTX 4090/5090 recommended
3. Copy this `runpod/` directory to `/workspace` on the pod (or clone the repo)
4. Run: `WORKSPACE=/workspace bash /workspace/runpod/bootstrap.sh`

## Pipeline scripts (`pipeline/`)

| Script | Purpose |
|--------|---------|
| `sync_docs.py` | `cortex-docs-sync` incremental mirror |
| `chunk_html.py` | HTML → hierarchical chunks |
| `embed_gpu.py` | BGE-M3 FP16 batch embeddings |
| `build_index.py` | LanceDB index |
| `export_snapshot.py` | `.tar.zst` + manifest |

Local orchestration: UI **Build / Update knowledge base** or `make sync-kb`.

See [docs/kb-sync-flow.md](../docs/kb-sync-flow.md) and ADR [002-runpod-connection.md](../docs/decisions/002-runpod-connection.md).
