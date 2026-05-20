#!/usr/bin/env bash
# Idempotent GPU pod bootstrap for SIWZ-RAG Lite KB pipeline
set -euo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
VENV="${WORKSPACE}/.venv"
MARKER="${WORKSPACE}/.bootstrap_ok"
RPOD_DIR="${WORKSPACE}/runpod"
LOG="${WORKSPACE}/bootstrap-pip.log"

export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
export PIP_PROGRESS_BAR=off
# Lower peak RAM during wheel unpack / metadata resolve
export PIP_REQUIRE_VIRTUALENV=1

log() { echo "[bootstrap] $*"; }

ensure_swap() {
  if swapon --show 2>/dev/null | grep -q swapfile; then
    return 0
  fi
  local mem_mb
  mem_mb=$(free -m | awk '/^Mem:/{print $2}')
  if [[ "${mem_mb}" -lt 32000 ]]; then
    log "Adding 8G swap (system RAM ${mem_mb}MB — avoids OOM during pip)..."
    if ! fallocate -l 8G /swapfile 2>/dev/null; then
      dd if=/dev/zero of=/swapfile bs=1M count=8192 status=none
    fi
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
  fi
}

pip_install() {
  # Sequential installs — one resolver/unpack at a time (avoids OOM on 24GB pods)
  local label="$1"
  shift
  log "pip: ${label}"
  local attempt
  for attempt in 1 2 3; do
    if "$VENV/bin/pip" install --no-cache-dir "$@" >>"$LOG" 2>&1; then
      return 0
    fi
    log "pip failed (${label}), attempt ${attempt}/3 — see ${LOG}"
    sleep 10
  done
  tail -n 40 "$LOG" >&2 || true
  return 1
}

verify_venv() {
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python - <<'PY'
import importlib.util
import sys

for mod in ("torch", "lancedb", "sentence_transformers", "FlagEmbedding"):
    if importlib.util.find_spec(mod) is None:
        print(f"missing:{mod}", file=sys.stderr)
        sys.exit(1)
import torch
assert torch.cuda.is_available(), "CUDA not available to PyTorch"
print("ok:", torch.cuda.get_device_name(0))
PY
}

log "Checking CUDA..."
if ! command -v nvidia-smi &>/dev/null; then
  log "ERROR: nvidia-smi not found"
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

if [[ -f "$MARKER" && -z "${FORCE_BOOTSTRAP:-}" ]]; then
  log "Marker present — verifying existing venv..."
  if verify_venv; then
    log "Already configured (set FORCE_BOOTSTRAP=1 to reinstall)"
    exit 0
  fi
  log "Marker stale, reinstalling..."
  rm -f "$MARKER"
fi

ensure_swap

log "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl rsync zstd >/dev/null || true

: >"$LOG"
if [[ ! -x "$VENV/bin/python" ]]; then
  log "Creating Python venv..."
  python3 -m venv "$VENV"
else
  log "Reusing existing venv at ${VENV}"
fi

pip_install "upgrade pip" --upgrade pip wheel setuptools

log "Installing PyTorch (CUDA 12.4 wheels)..."
pip_install "torch" torch --index-url https://download.pytorch.org/whl/cu124

pip_install "base" \
  "lancedb>=0.17.0" \
  "pyarrow>=18.0.0" \
  "selectolax>=0.3.27" \
  "tqdm>=4.66.0" \
  "requests>=2.31.0" \
  "zstandard>=0.22.0"

pip_install "sentence-transformers" "sentence-transformers>=3.0.0,<6"
pip_install "FlagEmbedding" "FlagEmbedding>=1.2.10,<2"

if ! command -v cortex-docs-sync &>/dev/null; then
  pip_install "cortex-docs-sync" \
    "cortex-docs-sync @ git+https://github.com/n0081183/cortex-docs-sync-v3.git"
fi

verify_venv
date -u +"%Y-%m-%dT%H:%M:%SZ" >"$MARKER"
log "Done. Pip log: ${LOG}"
