.PHONY: help dev-backend dev-frontend dev install-backend install-frontend install test test-cov lint lint-fix format build-frontend build-exe clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Development ──────────────────────────────────────────────

dev-backend: ## Start backend with auto-reload
	python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

install-backend: ## Install backend Python dependencies
	pip install -r backend/requirements.txt

install-frontend: ## Install frontend Node.js dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

# ── Testing ──────────────────────────────────────────────────

test: ## Run backend tests
	python -m pytest -q

test-cov: ## Run backend tests with coverage
	python -m pytest --cov=backend --cov-report=term-missing --cov-report=html

test-verbose: ## Run backend tests with verbose output
	python -m pytest -v --tb=long

# ── Linting & Formatting ────────────────────────────────────

lint: ## Lint backend and frontend
	ruff check backend/ tests/
	cd frontend && npm run lint

lint-fix: ## Auto-fix lint issues
	ruff check --fix backend/ tests/
	cd frontend && npm run lint -- --fix

format: ## Format backend code
	ruff format backend/ tests/

# ── Build ────────────────────────────────────────────────────

build-frontend: ## Build frontend for production
	cd frontend && npm run build

build-exe: build-frontend ## Build Windows .exe desktop app
	python scripts/build/build_exe.py

# ── Maintenance ──────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf frontend/dist frontend/node_modules
	rm -rf backend/__pycache__ backend/app/__pycache__
	rm -rf .pytest_cache .pytest_cache_local .pytest_tmp
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
