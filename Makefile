# SimplePod Swarm — Makefile
# ==========================
# ELI5: This is the master control panel with labeled switches.
#       Instead of remembering which breaker controls which room,
#       you just read the label and flip the switch.

.PHONY: help install test lint format build-docker run-docker dev stop clean

help:
	@echo "SimplePod Swarm — Available Commands"
	@echo "====================================="
	@echo "  make install      Install Python + Node dependencies"
	@echo "  make test         Run all tests"
	@echo "  make lint         Run ruff + mypy on Python code"
	@echo "  make format       Auto-format Python code with ruff"
	@echo "  make build        Build React frontend + VS Code extension"
	@echo "  make dev          Start backend in development mode"
	@echo "  make stop         Stop any running backend processes"
	@echo "  make docker-build Build Docker image"
	@echo "  make docker-run   Run full stack with docker-compose"
	@echo "  make docker-down  Stop docker-compose stack"
	@echo "  make clean        Remove build artifacts and caches"

# ---------------------------------------------------------------------------
# Development Setup
# ---------------------------------------------------------------------------
install:
	pip install -e ".[dev]" || pip install -e .
	cd interfaces/web_ui/frontend && npm install
	cd interfaces/vscode_extension && npm install
	pre-commit install || echo "pre-commit not installed (pip install pre-commit)"

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------
test:
	PYTHONPATH=. pytest tests/ -v --tb=short

test-cov:
	PYTHONPATH=. pytest tests/ -v --tb=short --cov=core --cov-report=term-missing

# ---------------------------------------------------------------------------
# Linting & Formatting
# ---------------------------------------------------------------------------
lint:
	ruff check core/ interfaces/web_ui/backend/ tests/ --line-length 100
	cd interfaces/vscode_extension && npx tsc --noEmit

format:
	ruff format core/ interfaces/web_ui/backend/ tests/ --line-length 100

# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------
build: build-frontend build-vscode

build-frontend:
	cd interfaces/web_ui/frontend && npm run build

build-vscode:
	cd interfaces/vscode_extension && npx tsc -p ./

# ---------------------------------------------------------------------------
# Development Server
# ---------------------------------------------------------------------------
dev:
	@echo "Starting SimplePod backend on http://127.0.0.1:8000"
	cd interfaces/web_ui && PYTHONPATH=../.. python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload --log-level info

stop:
	-pkill -f "uvicorn backend.main:app" || true

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
docker-build:
	docker build -t simplepod-swarm:latest .

docker-run:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f simplepod-swarm

# ---------------------------------------------------------------------------
# OrbitScribe Demo
# ---------------------------------------------------------------------------
orbitscribe:
	@echo "Running OrbitScribe synthetic analysis..."
	@curl -s "http://127.0.0.1:8000/unified/demo/orbitscribe/analyze?mode=synthetic" | python -m json.tool

orbitscribe-report:
	@echo "Opening OrbitScribe HTML report..."
	@start http://127.0.0.1:8000/unified/demo/orbitscribe/report?mode=synthetic || open http://127.0.0.1:8000/unified/demo/orbitscribe/report?mode=synthetic || xdg-open http://127.0.0.1:8000/unified/demo/orbitscribe/report?mode=synthetic

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -path "*/frontend/*" -prune -o -name node_modules -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned build artifacts"
