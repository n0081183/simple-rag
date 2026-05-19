# ADR 001: Vector database — LanceDB

## Status

Accepted (Milestone 0)

## Context

SIWZ-RAG Lite needs an embedded vector store that:

- Runs locally without Docker (contrast: v3 used Qdrant in Docker)
- Supports **hybrid search** (dense BGE-M3 + sparse lexical weights)
- Produces a **portable snapshot** (tar.zst) for RunPod → local transfer
- Handles ~60k chunks with acceptable query latency (<200ms p95 on laptop)

Candidates evaluated:

| Store | Hybrid (dense+sparse) | Portable snapshot | Docker | Notes |
|-------|----------------------|-------------------|--------|-------|
| **LanceDB** | Yes (FTS + vector, RRF in app layer) | Single directory | No | Arrow-native, lazy load |
| ChromaDB | Partial | Yes | No | Weaker sparse/hybrid |
| Qdrant embedded | Best hybrid | Heavier | No | Larger footprint, migration from v3 patterns |

## Decision

Use **LanceDB** as the primary vector store.

## Rationale

1. **Deployment**: Entire index is a directory tree — ideal for atomic swap (`kb-staging` → `kb-active`) and RunPod export.
2. **Hybrid**: Store dense vectors in Lance; sparse BGE-M3 weights serialized as JSON column; fuse with RRF in `retriever.py` (same pattern as v3 application-layer multi-query, DB-layer RRF per query).
3. **No ops burden**: No container, no separate process — matches “another developer clones in 30 minutes”.
4. **Scale**: 60k × 1024-dim FP32 ≈ 250MB dense only; fits comfortably on disk and in memory-mapped reads.

## Consequences

- RRF/hybrid logic lives partly in Python (not only DB-native like Qdrant `FusionQuery`) — acceptable; retrieval path is per-requirement, not high-QPS.
- PoC script: `scripts/poc_vector_db.py` (chunk sample → index → 10 queries).
- If hybrid quality regresses vs Qdrant in eval, reassess Qdrant **embedded** mode (ADR amendment), not Docker.

## References

- v3: `src/vectorstore.py` (Qdrant prefetch + RRF)
- LanceDB hybrid: https://lancedb.github.io/lancedb/hybrid_search/
