#!/usr/bin/env bash
# Full KB build pipeline on RunPod GPU pod
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
VENV="${WORKSPACE}/.venv"
INPUT_DIR="${INPUT_DIR:-${WORKSPACE}/cortex_docs}"
PRODUCTS="${PRODUCTS:-xdr xsiam xsoar xpanse cortex_cloud agentix}"
INCREMENTAL="${INCREMENTAL:-1}"
RATE_LIMIT="${RATE_LIMIT:-0.35}"
CORTEX_SYNC_TOPIC_WORKERS="${CORTEX_SYNC_TOPIC_WORKERS:-1}"
export CORTEX_SYNC_TOPIC_WORKERS
export CORTEX_ALLOW_PARTIAL="${CORTEX_ALLOW_PARTIAL:-1}"
INCLUDE_RN="${INCLUDE_RELEASE_NOTES:-0}"

# shellcheck disable=SC1091
source "$VENV/bin/activate"
export PYTHONUNBUFFERED=1
cd "$WORKSPACE"

echo "[pipeline] Products: $PRODUCTS"
echo "[pipeline] Incremental: $INCREMENTAL"

SYNC_ARGS=(--output-dir "$INPUT_DIR" --rate-limit "$RATE_LIMIT")
if [[ "$INCREMENTAL" != "1" ]]; then
  SYNC_ARGS+=(--full)
fi
if [[ "$INCLUDE_RN" == "1" ]]; then
  SYNC_ARGS+=(--include-release-notes)
fi
# Pass all products in one flag (avoids argparse swallowing only the last --product)
# shellcheck disable=SC2206
SYNC_ARGS+=(--products $PRODUCTS)

python runpod/pipeline/sync_docs.py "${SYNC_ARGS[@]}"

python runpod/pipeline/chunk_html.py \
  --input-dir "$INPUT_DIR" \
  --output "${WORKSPACE}/chunks.jsonl"

python runpod/pipeline/embed_gpu.py \
  --input "${WORKSPACE}/chunks.jsonl" \
  --output "${WORKSPACE}/embeddings.jsonl" \
  --batch-size "${EMBED_BATCH_SIZE:-64}"

python runpod/pipeline/build_index.py \
  --input "${WORKSPACE}/embeddings.jsonl" \
  --output-dir "${WORKSPACE}/kb_build"

python runpod/pipeline/export_snapshot.py \
  --input-dir "${WORKSPACE}/kb_build" \
  --output "${WORKSPACE}/kb_snapshot.tar.zst"

echo "[pipeline] Done: ${WORKSPACE}/kb_snapshot.tar.zst"
