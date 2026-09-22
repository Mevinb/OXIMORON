# OXIMORON

> Local-first desktop AI orchestration platform that manages models, inference engines, hardware resources, cloud providers, and AI tools through one interface.

**Install models once. Run them anywhere compatible. Control everything from one place.**

## Architecture & Principles

- **Local-First & Offline Capable:** Runs without internet connectivity once engines/models are configured.
- **Isolated Engine Process Lifecycle:** Manages independent engines (llama.cpp, Stable Diffusion WebUI Forge, Fooocus) without contaminating their Python or inference environments.
- **Single Authority Backend:** FastAPI service backed by SQLite and validated YAML configuration.
- **Tauri 2 Desktop Shell:** Fast, lightweight, secure desktop integration.

## Getting Started

### Prerequisites

- Python 3.12+ with [uv](https://github.com/astral-sh/uv)
- Node.js 20+ with `pnpm`
- Rust toolchain (optional for native Tauri compilation)

### Development Setup

```bash
# 1. Sync Python dependencies
uv sync --all-extras

# 2. Run backend test suite
uv run pytest

# 3. Start backend supervisor
uv run oximoron-backend

# 4. Use CLI
uv run oximoron status
```

## Documentation

- [Product & Architecture Plan](plan.md)
- [Implementation Backlog & Milestones](implementation.md)
- [Agent & Contributor Guidelines](agent.md)
- [Compatibility Matrix](docs/compatibility/matrix.md)
- [Architecture Decision Records (ADRs)](docs/adr/)
