#!/usr/bin/env bash
# Idempotent GPU pod bootstrap for SIWZ-RAG Lite KB pipeline
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
VENV="${WORKSPACE}/.venv"

echo "[bootstrap] Checking CUDA..."
if ! command -v nvidia-smi &>/dev/null; then
  echo "[bootstrap] ERROR: nvidia-smi not found"
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

echo "[bootstrap] Installing system packages..."
apt-get update -qq && apt-get install -y -qq git curl rsync zstd >/dev/null || true

echo "[bootstrap] Creating Python venv..."
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q --upgrade pip wheel

echo "[bootstrap] Installing GPU dependencies..."
pip install -q torch --index-url https://download.pytorch.org/whl/cu124
pip install -q -r "${WORKSPACE}/runpod/requirements.txt"

python - <<'PY'
import torch
assert torch.cuda.is_available(), "CUDA not available to PyTorch — abort"
print("[bootstrap] torch.cuda:", torch.cuda.get_device_name(0))
PY

echo "[bootstrap] Done."
