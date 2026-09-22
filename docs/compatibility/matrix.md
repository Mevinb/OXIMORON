# OXIMORON Compatibility & Environment Matrix

**Status:** Verified Baseline  
**Date:** 2026-09-22  
**Host:** Ubuntu Linux x86_64 (Linux 6.8.0-40-generic / glibc 2.39)  
**GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6141 MiB VRAM), Driver 595.84, CUDA 13.2  

---

## 1. Pinned Toolchain

| Tool | Version | Path | Verification Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.12.3 / 3.13.15 | `/usr/bin/python3.12`, `/home/mevlec/.local/bin/python3.13` | System Python 3.12.3 and uv-managed Python. Core backend runs on 3.12+. |
| **uv** | 0.12.6 | `/home/mevlec/.local/bin/uv` | Fast Python package manager, isolated venv management. |
| **Node.js** | 22.23.2 | `/usr/bin/node` | LTS Node runtime. |
| **pnpm** | 12.5.1 | `/home/mevlec/.local/bin/pnpm` (via npx runner) | Fast monorepo package manager for frontend workspace. |
| **Rust / Cargo** | 1.98.1 | `/home/mevlec/.cargo/bin/rustc`, `/home/mevlec/.cargo/bin/cargo` | Stable toolchain for Tauri 2 host and native packaging. |
| **Tauri** | 2.x | `@tauri-apps/cli` via pnpm / cargo | Desktop application wrapper. Runtime packages `libwebkit2gtk-4.1-0` installed. |

---

## 2. Installed Engine Compatibility Inventory

| Engine | Version / Build | Executable / Python Path | Status & Verified Capabilities |
| :--- | :--- | :--- | :--- |
| **llama.cpp** | `0.3.0-dev (build 1, commit bebc935)` | `/home/mevlec/llama.cpp/build/bin/llama-server` | **Supported & Verified**. Built with CUDA acceleration (`libggml-cuda.so.0.22.0`). Flags: `--host`, `--port`, `-m`, `-c`, `-ngl`, `--api-key`. Route `GET /health` available. |
| **Stable Diffusion WebUI Forge** | Fork with API module (`2026-08/09`) | Script: `/home/mevlec/Data/forge/run.sh`<br>Python: `/home/mevlec/Data/forge/stable-diffusion-webui-forge/venv/bin/python` | **Supported & Verified**. PyTorch 2.3.1+cu121 with CUDA enabled. Supports `--api`, `--nowebui`, `--port`, `--listen 127.0.0.1`, `--skip-load-model-at-start`. |
| **Fooocus** | 2.x | Script: `/home/mevlec/Data/foocus/entrypoint.sh`<br>Python: `/home/mevlec/Data/foocus/fooocus_env/bin/python` | **Lifecycle Supported**. PyTorch 2.12.1+cu130 with CUDA enabled. Supports `--listen 127.0.0.1`, `--port`. Generation bridge deferred per plan. |
| **ComfyUI** | 0.x | Standalone `/home/mevlec/ComfyUI` and `/home/mevlec/Data/ComfyUI` | **Deferred (v0.3)**. Candidate directories discovered with empty model folders. |

---

## 3. Discovered Model Assets

| Model Name / File | Format | Size | Engine / Role | Location |
| :--- | :--- | :--- | :--- | :--- |
| `flux1-dev-Q3_K_S.gguf` | GGUF | 4.9 GB | Forge / UNet Diffusion | `/home/mevlec/Data/forge/stable-diffusion-webui-forge/models/Stable-diffusion/` |
| `juggernautXL_juggXILightningByRD.safetensors` | Safetensors | 6.7 GB | Forge / SDXL Checkpoint | `/home/mevlec/Data/forge/stable-diffusion-webui-forge/models/Stable-diffusion/` |
| `lustifyNSFWCheckpoint_endgame.safetensors` | Safetensors | 6.5 GB | Forge / SD Checkpoint | `/home/mevlec/Data/forge/stable-diffusion-webui-forge/models/Stable-diffusion/` |
| `t5-v1_1-xxl-encoder-Q4_K_M.gguf` | GGUF | - | Forge / Text Encoder | `/home/mevlec/Data/forge/stable-diffusion-webui-forge/models/text_encoder/` |
| `clip_l.safetensors` | Safetensors | - | Forge / Text Encoder | `/home/mevlec/Data/forge/stable-diffusion-webui-forge/models/text_encoder/` |
| `ggml-vocab-*.gguf` | GGUF | 600K - 16M | llama.cpp / Vocab & Test | `/home/mevlec/llama.cpp/models/` |

---

## 4. Subsystem Investigation Findings

1. **Tauri Webview Prerequisites (Ubuntu 24.04):**
   - Runtime libraries `libwebkit2gtk-4.1-0`, `libayatana-appindicator3-1`, `librsvg2-2` are installed and verified.
   - Development builds of Tauri require GTK and WebKit dev headers if compiling Rust host directly; Web UI runs via Vite dev server.

2. **NVML / GPU Telemetry:**
   - `/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1` is present.
   - Verified direct `nvmlInit()` via ctypes and `pynvml`. Real GPU VRAM and utilization telemetry is fully functional.

3. **Keyring / Secrets:**
   - `gnome-keyring` (version 46.1) is installed.
   - Session-only fallback storage is implemented strictly for local API token when keyring daemon is locked/headless. Cloud keys are never written to plaintext.

4. **Process & Process Groups:**
   - Linux `setpgid` and `os.killpg` are available for clean child/grandchild tree termination without orphaning background inference servers.
