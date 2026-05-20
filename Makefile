.PHONY: install dev build run eval sync-kb lint test preflight clean

UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
PYTHON := backend
FRONTEND := frontend
DATA_DIR ?= $(HOME)/.siwz-rag-lite

export PATH := $(HOME)/.local/bin:$(PATH)
export SIWZ_DATA_DIR := $(DATA_DIR)

install: ## Install Python (uv) and frontend dependencies, build UI
	@echo "==> Installing Python dependencies..."
	$(UV) sync --all-extras
	@echo "==> Installing frontend dependencies..."
	cd $(FRONTEND) && npm ci
	@echo "==> Building frontend..."
	$(MAKE) build
	@echo "==> Done. Run 'make run' to start."

dev: ## Run backend + frontend in development mode
	@echo "Starting backend (reload) and frontend dev server..."
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd $(PYTHON) && $(UV) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd $(FRONTEND) && npm run dev

build: ## Build Next.js static export for FastAPI
	cd $(FRONTEND) && npm run build

run: build ## Production: FastAPI serves API + static frontend
	cd $(PYTHON) && $(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000

eval: ## Run gold-set evaluation pipeline
	$(UV) run python eval/run_eval.py

sync-kb: ## CLI fallback: dry-run seed KB (no RunPod)
	cd backend && $(UV) run python -c "from app.api.kb import SyncStartRequest; from app.jobs.kb_sync import run_kb_sync_job; run_kb_sync_job('cli', SyncStartRequest(dry_run=True), {})"

lint: ## Ruff + mypy + frontend lint
	$(UV) run ruff check backend eval
	$(UV) run ruff format --check backend eval
	cd $(FRONTEND) && npm run lint

test: ## pytest + vitest
	$(UV) run pytest backend/tests -q
	cd $(FRONTEND) && npm run test --if-present

preflight: ## Check environment (Ollama, KB path, GPU optional)
	$(UV) run python scripts/preflight.py

seed-kb: ## Build seed knowledge base (local dev)
	$(UV) run python scripts/ingest_seed_kb.py

clean:
	rm -rf $(FRONTEND)/.next $(FRONTEND)/out $(FRONTEND)/node_modules/.cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
