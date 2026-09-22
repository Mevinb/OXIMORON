# ADR 0001: Sidecar Process Architecture for Desktop and Engines

## Status
Accepted (2026-09-22)

## Context
OXIMORON coordinates multiple native components:
1. A desktop user interface.
2. A single authoritative backend orchestrator that manages hardware, databases, and configuration.
3. Third-party inference engines (llama.cpp, Stable Diffusion WebUI Forge, Fooocus).

Embedding heavy inference dependencies (PyTorch, CUDA, Transformers) directly into the manager's Python environment would cause massive dependency bloat, fragile version conflicts, and startup latency. Furthermore, running multiple instances of the backend orchestrator would lead to race conditions over ports, model sessions, and GPU allocations.

## Decision
1. **Desktop Shell:** Built using Tauri 2 (Rust + Webview). The desktop shell is responsible for window lifecycle, system tray integration, and bootstrapping or attaching to the backend.
2. **Backend Orchestrator:** Written in Python using FastAPI + Pydantic. Runs as a single supervisor process per OS user / data directory, enforcing a single-instance lock (`.supervisor.lock`).
3. **Inference Engines:** Managed as independent external processes in their own process groups (`setpgid`). The backend communicates with them over validated loopback HTTP/API endpoints (`127.0.0.1`).
4. **Environment Isolation:** OXIMORON maintains its own isolated virtual environment (managed by `uv`). It never imports PyTorch or modifies the virtual environments of Forge or Fooocus.

## Consequences
- **Positive:** No dependency pollution or CUDA version collisions between engines. Clean crash boundaries: if an inference engine crashes or runs out of VRAM, the OXIMORON backend remains responsive and can clean up gracefully.
- **Negative:** Engine lifecycle requires rigorous process supervision, creation-time checks, and process group management to avoid orphaned inference processes.
