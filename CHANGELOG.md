# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.6.0] - 2026-06-03

### Added

- **OrbitScribe Relationship Engine** — LLM-powered relationship reasoning with chain-of-thought evidence
  - Attachment style detection (secure, anxious, avoidant, disorganized)
  - Triangulation event identification with manipulative scoring
  - Emotional trajectory mapping with inflection points
  - Relationship graph with centrality and risk analysis
  - 3-mode operation: instant synthetic, auto fallback, full LLM
  - Parallel execution via ThreadPoolExecutor
  - Compact prompts for Ollama compatibility
- `/unified/demo/orbitscribe/analyze` JSON API endpoint with mode selector
- `/unified/demo/orbitscribe/report` styled HTML report page
- **React frontend integration** — dedicated `/orbitscribe` page with sidebar nav and Tools grid
- **VS Code Extension** — `OrbitScribe: Relationship Analysis` command with mode picker
- **Android App** — `SimplePodUnified` native Android client
  - Floating ChatHead overlay (`SYSTEM_ALERT_WINDOW`)
  - SMS/MMS conversation analysis
  - AI reply generator with tone/goal selectors
  - 20-worker swarm status monitor
  - OrbitScribe relationship analysis screen
- **Phone Simulator** — 5-contact love-triangle dataset (Sarah, Derek, Marcus, Jessica, Mom)
  - 203 messages across 5 threads
  - 11 call logs, 6 media items, 7 GPS locations
- **SimplePod Unified Core** — 20-node asyncio worker swarm
  - Orchestrator, State Manager, Vision Engine, OS Interface, Self-Healing
  - File System I/O workers, LLM query workers, Error Catcher, Telemetry, Health Monitor
- **FastAPI Integration** — REST + WebSocket endpoints in `routers/unified.py`
- **LLM Fallback** — Auto-fallback from Ollama → Pollinations.AI (free, no signup)
- **Self-Healing Engine** — Autonomous CI/CD loop with LLM-generated patches
- **Project Launcher** — Fixed FastAPI apps to use `uvicorn` instead of `python app.py`
- **GitHub Actions CI** — pytest, TypeScript compile, React build on every push/PR
- **Pre-commit hooks** — ruff, mypy, pytest, tsc checks
- **Makefile** — `install`, `test`, `lint`, `format`, `build`, `dev`, `docker-run`, `orbitscribe`
- **Docker + docker-compose** — Backend + Ollama sidecar, health checks, persistent volumes
- **CLI entry point** — `simplepod server`, `simplepod orbitscribe`, `simplepod test`, `simplepod version`

### Fixed

- `SelfHealingConfig` missing `ark_backup_dir` attribute causing `AttributeError`
- Unicode printing errors in `phone_analyzer.py` (`PYTHONIOENCODING=utf-8`)
- VS Code extension TypeScript compile errors (`game` property, `disposed` property)
- Desktop shortcut using broken UTF-8 box characters — replaced with PowerShell script
- LLM fallback timeout too short for Ollama cold starts (30s → 60s)
- Pollinations.AI rate limiting — added `User-Agent` header

### Changed

- `pyproject.toml` coverage source from `src/simplepod` to `core`
- `pyproject.toml` URLs updated to `sevengramdab/simplepod-v2`
- `Dockerfile` now sets `PYTHONPATH=/app` for containerized module resolution

## [2.5.0] and earlier

- Initial swarm architecture with mesh networking
- OrbStudio thermal monitoring
- Shadow PC remote control bridge
- SwarmCoder code generation pipeline
- Project discovery and launcher
