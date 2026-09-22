# Test Strategy & Engine Testing Boundaries

## 1. Principles

1. **Deterministic CI by Default:** Automated tests run without relying on installed third-party engines, GPU hardware, internet connectivity, or paid API keys.
2. **Synthetic Contract Fixtures:** Adapters are tested against synthetic fixtures and mock HTTP servers reproducing exact upstream wire protocols.
3. **Explicit Opt-In for Live Verification:** Real engine execution (llama.cpp, Forge, Fooocus) and GPU stress tests require explicit pytest flags/markers (`--live-engines`, `--gpu`).
4. **Honest Evidence:** Test suites report whether a capability was verified via synthetic contract or actual live engine execution.

## 2. Test Classification

| Marker / Layer | Environment Required | What It Proves |
| :--- | :--- | :--- |
| `unit` | Python environment only | Business logic, Pydantic schemas, routing algorithms, YAML serialization, state machine transitions. |
| `contract` | Offline mock server | Adapter HTTP client request/response translation, SSE token parsing, error code normalization against recorded API schemas. |
| `integration` | Local SQLite + temporary dirs | Process manager spawn/kill, process group isolation, database migrations, atomic writes, single-instance supervisor lock. |
| `live_engine` | Real engine binaries (llama.cpp / Forge) | Process launches successfully, binds loopback port, passes health check, performs inference on selected test model, shuts down cleanly. |
| `hardware` | NVIDIA GPU with NVML | VRAM allocation monitoring, temperature/power polling, GPU conflict prevention. |
| `e2e` | Frontend + Backend | Full user journey: startup, model discovery, chat stream, generation queue, settings save. |

## 3. Mocked vs Live Verification Matrix

- **Mocked Engine Tests:**
  - Mock llama.cpp server responding with OpenAI-compatible streaming chunks (`data: {"choices": [{"delta": {"content": "..."}}]}`).
  - Mock Forge server responding with `/sdapi/v1/txt2img` and `/sdapi/v1/progress`.
  - Simulates engine delays, timeouts, 500 errors, process crashes, and port conflicts.
- **Live Engine Tests:**
  - Validates actual executable `/home/mevlec/llama.cpp/build/bin/llama-server`.
  - Validates actual Forge script `/home/mevlec/Data/forge/run.sh`.
  - Uses discovered models on the machine.
