#!/usr/bin/env bash
# Run Playwright E2E against built frontend + FastAPI (heuristic extraction).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"
export SIWZ_SKIP_ML=1
export SIWZ_E2E=1

cd "$ROOT"
echo "==> Building frontend..."
make build

echo "==> Installing Playwright..."
cd e2e
npm ci
npx playwright install chromium

echo "==> Running E2E tests..."
npm test
