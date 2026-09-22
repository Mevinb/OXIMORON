# OXIMORON — Product and Architecture Plan

Status: planning only; no application implementation authorized by this document.
Planning baseline: 2026-09-22.

> A local-first AI orchestration platform that manages models, inference engines, hardware resources, cloud providers, and AI tools through one interface.

**Install models once. Run them anywhere compatible. Control everything from one place.**

## 1. How to use these documents

| Document | Purpose | Authoritative for |
| --- | --- | --- |
| [plan.md](plan.md) | Product definition, architecture, scope, release gates, risks | What to build and why |
| [implementation.md](implementation.md) | Contracts, schemas, algorithms, ordered work packages, verification | How to build and prove it |
| [agent.md](agent.md) | Instructions for future contributors and coding agents | How to work safely within the approved scope |

Read them in that order. This is a complete planning baseline, not evidence that any feature exists. All work packages begin as **not started**. Proposed commands, layouts, endpoints, settings, and schemas describe future implementation. Only these three Markdown files are deliverables of the current task.

Quick navigation: [release scope](#4-scope-by-release) · [v0.1 finish line](#5-v01-definition-of-done) · [user experience](#6-user-experience) · [architecture](#7-system-architecture) · [storage](#10-model-library-and-storage) · [security](#16-security-and-privacy-model) · [delivery order](#20-delivery-order-and-effort-assumptions) · [all 57 requirements](#21-traceability-to-the-complete-brief).

When implementation is requested later, begin with M00 in `implementation.md`, then advance through the dependency order. A request to start v0.1 does not authorize building every later release. Changes to this baseline must update the affected contracts and acceptance criteria together.

## 2. Product boundaries

### 2.1 What OXIMORON owns

- A desktop control surface, CLI, and authenticated localhost API.
- Registration and discovery of installed engines and existing model files.
- The lifecycle of processes it starts, including ports, readiness, logs, cancellation, and recovery.
- Selection of compatible engines/models according to user policy and hardware availability.
- Its own metadata, conversations, generations, workspaces, settings, and job history.
- Explicit permission decisions for future tools and external integrations.

### 2.2 What OXIMORON does not own

- Inference kernels, model training, image pipelines, or third-party engine internals.
- Unrelated AI processes that happen to be running on the computer.
- Automatic deletion, relocation, conversion, or replacement of existing model files.
- The user's whole filesystem, shell session, GPU driver installation, or system package manager.
- A guarantee that one model format works in every engine. Shared storage does not imply format compatibility.

Engine installations remain separate environments. OXIMORON does not merge Forge, Fooocus, and its own Python dependencies into one virtual environment. No model weights or CUDA/PyTorch runtime are bundled with the manager by default.

### 2.3 Initial audience and supported baseline

Initial target: one local user on Ubuntu/Linux x86_64, with an optional NVIDIA GPU. CPU-only systems must launch and remain usable for supported local chat. The RTX 4050 6 GB / 16 GB RAM machine in the brief is a reference test configuration, not a detected fact or a hardcoded default.

Windows support is an architectural constraint from the beginning and a release qualification target for v1.0. macOS is not a committed release target. Network filesystems, remote multi-user hosting, containers as the default runtime, and distributed scheduling are outside v0.1.

## 3. Non-negotiable principles

1. **Offline first:** installed and provisioned local engines, files, settings, history, and the UI work without internet. Initial installation/downloads may require internet; missing assets must be reported before a supposedly offline run.
2. **Explicit data boundary:** Local mode never silently falls back to cloud. Private profile disables all OXIMORON-initiated non-loopback network activity, including catalog refreshes, update checks, remote MCP, and cloud calls.
3. **No manager-created duplicate weights by default:** register in place first; use supported shared paths or symlinks later. Never silently copy an 8 GB model for another engine.
4. **Ownership before control:** only verified owned processes may be automatically stopped, restarted, or reclaimed for memory.
5. **Truthful capability reporting:** unknown hardware values are unknown; unsupported adapter methods stay unsupported; healthy HTTP does not by itself prove inference works.
6. **One backend authority:** UI, tray, CLI, and external clients use the same orchestrator, policies, state, and resource queue.
7. **Low overhead:** no inference model is loaded just to show a dashboard. A routing model is optional and deferred.
8. **Reversible integration:** preview and record external configuration/symlink changes, preserve originals, and provide rollback.
9. **Safe defaults:** loopback binding, authenticated control API, restricted origins, no telemetry by default, no automatic sudo, and no arbitrary shell construction.
10. **Evidence before release:** mocked adapters establish contracts; actual engine runs establish compatibility; actual desktop runs establish packaging and tray behavior.

Private profile is an application policy, not a claim that arbitrary third-party engines cannot access the network. Strict OS-enforced network isolation is a later opt-in feature with separate platform testing. Display this distinction clearly in settings.

## 4. Scope by release

| Release | Outcome | Included | Explicitly deferred |
| --- | --- | --- | --- |
| v0.1 — Local control center | Start existing engines, chat locally, generate through Forge, inspect files/hardware/logs | Tauri shell; FastAPI; SQLite/migrations; authentication; settings; bounded discovery; process/port manager; llama.cpp + Forge adapters; Fooocus lifecycle adapter; model scan; basic chat; basic generation; minimal durable records; telemetry; basic CLI; local API; basic command palette | Cloud; automatic cross-engine eviction; tool execution; downloader; model relocation/symlink writes; ComfyUI; plugin loading |
| v0.2 — Policy and intelligence | Route work, preserve history, switch resources safely | Deterministic router; Auto/Local/Cloud/Image UX; cloud providers; VRAM reservations + automatic idle unload; recommendations; full conversation/generation history; model switching; recovery UI; environment restoration; workspaces; profiles; tray/autostart/session restore; global search | Third-party plugin execution; autonomous tools; broad image editing; model marketplace |
| v0.3 — AI workstation | Share/download models and use advanced image workflows | ComfyUI; Ollama; verified Fooocus generation bridge if feasible; explicit engine installation recipes; resumable downloads + Hugging Face; LoRA/VAE/ControlNet management; gallery; symlinks; image editing/upscale; download queue | General-purpose agent tool execution; marketplace installation |
| v0.4 — Controlled agents | Execute scoped tools under enforceable permissions | Filesystem; terminal; Git; Python; browser integration; MCP; tool calling; approvals/auditing; bounded agent workflows | Unreviewed marketplace execution; remote multi-user product |
| v1.0 — Extensible runtime | A packaged, versioned platform for integrations | Plugin SDK and marketplace architecture; export/import and workspace sharing; opt-in remote API and web/phone client; multi-GPU; Linux + Windows installers; signed updates | Public marketplace operations and mobile-native apps unless separately scoped |

Two deliberate sequencing decisions:

- v0.1 includes durable conversation/message and generation records to avoid losing user work; rich history, search, branching, and gallery UX are later.
- v0.1 includes ownership checks, stale-process reconciliation, and resource conflict rejection. v0.2 adds automatic recovery and eviction workflows. Safety is not postponed with convenience features.

## 5. v0.1 definition of done

A user with existing compatible llama.cpp and Forge installations can:

1. Launch the desktop app with internet disconnected and no running engine.
2. Complete setup using detected candidates or manual paths without modifying those installations.
3. Scan selected directories and see GGUF/safetensors files without moving or loading them.
4. Start a selected GGUF model with llama.cpp; see loading, readiness, logs, and failure states.
5. Send a local message, receive streamed text, cancel a response, and reopen the saved conversation.
6. Stop the owned chat engine, start Forge, select a compatible checkpoint, generate an image, and reopen its saved file and metadata.
7. See CPU/RAM/storage and supported GPU metrics, including unavailable/stale indicators.
8. Start/stop/open a configured Fooocus installation, with integrated generation explicitly marked unsupported unless verified.
9. Use CLI status, engine control, local ask, and Forge generation through the same backend.
10. Recover gracefully from invalid paths, occupied ports, engine startup failure, a missing GPU, a failed request, and backend restart.
11. Exit cleanly with an explicit engine shutdown policy. No unrelated process is killed, model deleted, secret exposed, or request sent to cloud.

Release requires all v0.1 automated checks plus real llama.cpp/Forge and packaged Linux smoke tests. If hardware is unavailable, record the gap and label the build an unqualified preview; do not mark the gate passed.

## 6. User experience

### 6.1 First launch

1. Show the product purpose and local data directory choices.
2. Detect hardware without launching models. Show missing NVIDIA telemetry as a supported degraded state.
3. Offer candidate discovery under a short, visible list of approved folders. Do not recursively inspect the entire home directory by default.
4. Present engine candidates with paths and evidence. Selecting/configuring a candidate is distinct from executing it.
5. Let the user validate an executable, select an existing model root, and set preferred chat/image engines.
6. Show exactly what automatic configuration will change; v0.1 writes OXIMORON config only.
7. Finish at Home even if no engines or models exist. Manual setup remains accessible.

Empty state: “No local model configured. Add an existing model folder.” It must not initiate a download, launch, or cloud signup.

### 6.2 Navigation and page contract

| Page | Main purpose and actions | First release |
| --- | --- | --- |
| Home | Ask/Create entry points; real system summary; active engines; recent activity | v0.1 |
| Chat | Model selector; streamed Markdown/code; stop/retry; system prompt; sampling/context controls; saved conversations | v0.1 basics; attachments/vision v0.2 |
| Create | Prompt/negative prompt; engine/checkpoint; width/height; steps/CFG/sampler/seed; generate/cancel; output metadata | v0.1 Forge; advanced controls v0.3 |
| Models | Search/filter installed files; detail/compatibility; run; favorite; missing-file status | v0.1; discover/download v0.3 |
| Engines | Candidate setup; start/stop/restart/open; readiness; selected model; managed/external state | v0.1 |
| Workspaces | Photography/Development/Private presets and user-defined scoped configuration | v0.2 |
| Tools | Tool registry, permission requests/history, MCP connections | v0.4 |
| Downloads | Queue; speed/progress; pause/resume/cancel; verification; errors | v0.3 |
| Gallery | Image grid; filters; detail/provenance; reuse/variation/img2img/upscale | v0.3; recent results v0.2 |
| System | CPU/RAM/GPU/storage; per-owned-process usage; resource reservations | v0.1 basics; reservations v0.2 |
| Logs | OXIMORON and per-engine sources; severity/search; bounded tail; redacted export | v0.1 |
| Settings | Paths, ports, privacy, engines, shutdown, retention; later provider/profile/download settings | v0.1 onward |

Future pages are hidden or clearly described as planned; do not ship clickable controls that appear functional but do nothing. Each implemented screen needs loading, empty, success, failure, disconnected, and unsupported states.

### 6.3 Modes versus profiles

Modes describe request destinations. Profiles describe policy/preferences. They are separate controls.

| Mode | Meaning | Failure behavior |
| --- | --- | --- |
| Auto | Deterministic intent and compatible backend selection under policy | Ask for a selection when uncertain; no silent cloud fallback |
| Local | Only registered local engines on validated loopback endpoints | Explain unavailable local capability |
| Cloud | Only explicitly configured cloud providers | Explain offline/unconfigured provider; switching to local is user-visible |
| Image | Enter Create and request image capability | Apply workspace locality policy; initially local engines only |

In v0.1, Local chat and local Image are functional. Auto and Cloud are not advertised as implemented. In v0.2, an explicit “use ChatGPT” request can select a configured OpenAI API provider, but an existing ChatGPT subscription is not treated as API credentials. Private/Local policy still overrides this request with an explanation.

Policy precedence: hard security boundaries → Private/locality restrictions → explicit request selection → workspace defaults → profile preferences → application defaults. A profile may never relax a stricter workspace restriction. Invalid combinations are explained before submission.

| Profile | Planned effect | Constraints |
| --- | --- | --- |
| Fast | Prefer smaller registered models and shorter generation presets | No automatic download or arbitrary model substitution |
| Quality | Prefer higher quality compatible configured models and settings | Must pass resource checks |
| Private | Local only; disable non-loopback OXIMORON networking and remote tools | Does not claim OS sandboxing of third-party programs |
| Battery | Prefer light CPU work and conservative settings | Do not alter system power limits; show likely speed cost |
| Maximum | Highest configured quality/context within limits | Never bypass permissions, resource safety, or thermal limits |

### 6.4 Principal flows

**Chat:** select workspace/mode/model → submit → show routing decision if automatic → prepare engine → stream → save final or partial result → display measured tokens/context when available. Estimated context counts must be labeled estimates.

**Image:** set prompt/settings → preview resolved engine/model → submit job → wait for resources/permission → prepare → progress → durable output → reuse settings or open file. A progress estimate is not a guarantee of completion time.

**Resource conflict:** show current usage, uncertainty, requested workload, and affected owned idle engine → offer “Unload Qwen and continue” or cancel → recheck after permission → unload → verify release → proceed. v0.1 offers explicit manual stop followed by retry; v0.2 automates the approved sequence.

**Crash:** preserve job/partial output and recent logs → identify engine/backend failure → reconcile ownership/readiness → offer a safe restart. Never silently resubmit a cloud chargeable request or generate a second image after an ambiguous timeout.

**Previous environment:** after a deliberate switch, save engine/model/context/profile → once the new workload is idle offer restore → revalidate resources and files → restore or report why it cannot happen. Do not restore a stale PID or replay a prompt.

### 6.5 Visual identity and interaction

- Dark neutral foundation, one bright electric accent, restrained translucency, geometric O/X mark.
- Readable status text alongside color; clear focused/hover/disabled/destructive states.
- Sidebar grouped into work, resources, and administration; secondary destinations may be collapsible.
- Keyboard access throughout; Ctrl+K for command palette; Escape closes overlays or opens cancel confirmation when needed.
- Command palette actions use structured API commands. “Start Forge” is not raw shell text.
- Global search eventually spans models, conversations, generations, workspaces, and settings; results are grouped by type and respect workspace scope.
- Support reduced motion, scalable text, accessible contrast, long file paths, and responsive desktop window sizes.
- Heavy image grids/logs use virtualization and bounded caches; no permanent high-frequency animation.

## 7. System architecture

```text
Tauri desktop / tray       CLI            Other local clients
        |                  |                     |
        +---------- authenticated local API -----+
                             |
                      FastAPI transport
                 REST + SSE + event WebSocket
                             |
                        Orchestrator
          +------------------+------------------+
          |                  |                  |
     Policy + router    Job/resource queue   Model registry
          |                  |                  |
          +---------- Engine/provider services -+
                             |
             Adapter contracts + process manager
          +-------------+-------------+--------------+
          |             |             |              |
      llama.cpp        Forge       Fooocus       Later engines

Supporting services: SQLite, configuration, logs, hardware, secrets,
artifact storage, permissions, downloads, workspaces, tools/plugins.
```

### 7.1 Technology decisions

| Concern | Decision | Reason/boundary |
| --- | --- | --- |
| Desktop | Tauri 2 + small Rust host | Window/tray/native integration and backend bootstrap |
| Frontend | React + TypeScript + Vite | Desktop application UI; no SSR requirement |
| Styling | Tailwind CSS + shared design tokens | Consistency without choosing a giant component framework upfront |
| UI data | TanStack Query for server state; small local UI state store | Backend stays authoritative; avoid mirrored engine state |
| Backend | Python + FastAPI + Pydantic | Async control plane with validated contracts |
| HTTP clients | Shared async HTTP client with explicit deadlines | Pooling, cancellation, bounded retries |
| Persistence | SQLite + SQLAlchemy + Alembic | Relational registry with versioned migrations |
| Transport | REST for commands; SSE for chat; WebSocket for shared events | Streaming tokens and shared status have different lifecycles |
| Monitoring | psutil; NVIDIA NVML through maintained Python bindings | Optional GPU provider; graceful absence |
| Configuration | Validated YAML, written atomically | Human-readable portable operational settings |
| Secrets | OS keyring; session-memory fallback only by explicit choice | Never fallback to plaintext credentials |
| CLI | Python Typer client packaged with backend tooling | One API contract; no second process manager |
| Packaging | PyInstaller backend sidecar + Tauri Linux bundle initially | Manager dependencies bundled independently of engines |
| Tooling | uv for Python; pnpm for frontend; Cargo for host | Lockfiles committed during implementation |

Exact dependency versions are selected and pinned in M00 after compatibility checks; these docs do not invent future version guarantees. Tauri documents embedding externally packaged executables, including Python API servers, as sidecars. Packaging must be built and tested per target architecture. [Tauri sidecars](https://v2.tauri.app/develop/sidecar/)

### 7.2 Runtime ownership

- One backend supervisor per OS user/data directory, with a per-user lock and an authenticated discovery record.
- Desktop starts it when absent and attaches when a verified instance already exists. CLI reports absence unless `serve` or an explicit start option is used.
- FastAPI runs a single application worker in v0.1. Multiple workers would duplicate in-memory locks, engine ownership, and queues.
- Rust manages only backend bootstrap and desktop lifecycle. Python alone owns inference engine process management.
- Engine processes run in separate process groups; Windows support uses equivalent job/process-tree handling when implemented.
- GUI closure and full application exit are separate. Default v0.1 close asks to stop owned engines and quit; tray persistence arrives in v0.2.
- Graceful full exit cancels/drains owned jobs, stops verified owned engines, persists state, and shuts down the backend. A future explicit “leave engines running” option must expose reconnection consequences.

### 7.3 Service boundaries

| Service | Responsibilities | Must not do |
| --- | --- | --- |
| Router | Intent classification; explainable candidate ranking | Launch processes, override locality, grant permissions |
| Orchestrator | Job lifecycle; policy/resource preparation; execution and compensation | Implement engine-specific HTTP schemas |
| Engine service | Adapter registry, capabilities, engine configuration | Kill arbitrary PIDs |
| Process manager | Spawn, ownership proof, stream logs, readiness supervision, termination | Pick semantic model preferences |
| Resource manager | Snapshots, admission, reservations, idle/restore policy | Kill external processes or promise exact VRAM estimates |
| Model service | Scan, metadata, locations, compatibility and usage | Deserialize executable checkpoint payloads |
| Chat/generation services | Normalize requests and persist outputs/history | Bypass the orchestrator |
| Provider service | Cloud protocol translation, credentials, limits | Store keys in config or silently change locality |
| Permission service | Evaluate, request, bind, expire and audit approvals | Accept an LLM's own approval as user consent |
| Tool/download/workspace services | Their own scoped workflows | Become independent policy authorities |

## 8. Engine integration strategy

Every adapter exposes a capability descriptor and operations for detect, validate, install-plan, start, stop, restart, health, load, unload, and execution where supported. An unsupported operation returns a typed error. An `install()` hook does not mean automatic installation is in v0.1.

| Engine | Early integration | Important limits | Later work |
| --- | --- | --- | --- |
| llama.cpp | Registered executable; GGUF launch; readiness; streamed chat; owned shutdown | Flags, template support, multimodal projectors, load/unload behavior vary by build | Embeddings/vision/tool capability probes; optimized model switching |
| Forge | Registered installation/interpreter; API-enabled launch; checkpoint list; basic txt2img; progress; interrupt where verified | Do not assume all samplers/models/extensions share the same API behavior | img2img, inpaint, ControlNet, LoRAs, upscale |
| Fooocus | Discover/configure/start/stop/open UI | Integrated generation unavailable until a bridge is validated | Optional pinned bridge; never silently install a fork |
| ComfyUI | Deferred | Workflow JSON is a graph with model/node dependencies, not a plain prompt API | v0.3 workflow templates, queue/history, node validation |
| Ollama | Deferred | Managed service/model storage differs from a standalone GGUF server | v0.3 existing daemon attach; verify import/storage behavior before promising no-copy reuse |

llama.cpp exposes server health and OpenAI-compatible chat routes; compatibility is always tested against the installed build. Native tool features, if present, must stay disabled until OXIMORON's permission system mediates them. [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

Forge has an API implementation, but engine availability and individual capabilities must be probed rather than inferred from a UI port. [Forge API source](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/api/api.py)

Fooocus documents limited long-term support and an SDXL focus. The planning conclusion is to preserve a useful lifecycle adapter while treating any integrated generation bridge as an explicit compatibility investigation. This is not a claim that no API integration is possible. [Fooocus README](https://github.com/lllyasviel/Fooocus/blob/main/readme.md)

## 9. Discovery, processes, and ports

Discovery is read-only: configured paths → known shallow candidates within selected roots → optional bounded search. Record evidence such as executable names, entrypoint files, environment paths, and known repository markers. Do not execute arbitrary candidate scripts to identify them. Version execution happens only after registration and validation.

Process records include engine instance, PID, creation time, executable identity, command fingerprint, port, selected model, start/exit time, ownership, resource samples, logs, and exit reason. PID alone is never sufficient because PIDs are reused.

Engine state and job state are distinct. A running process may be starting, loading, ready, busy, degraded, stopping, failed, or external. “Ready” requires an engine-specific health check and expected identity, not simply an open TCP port.

Default ports: OXIMORON 6969, llama.cpp 8080, Forge 7860, Fooocus 7865, ComfyUI 8188; Ollama uses its configured service port. Port checks are advisory until bind succeeds. Serialize starts, retry a bounded range on verified bind conflicts, and record the actual endpoint. An unrelated service on 6969 must not receive tokens or be mistaken for OXIMORON.

Reconnect validates the data-directory instance, process identity, endpoint identity, and ownership record. Discovered external engines may be attached for explicitly authorized use; attaching does not grant automatic lifecycle or resource-eviction ownership.

## 10. Model library and storage

### 10.1 Recognition and metadata

Recognize GGUF, safetensors, ckpt, ONNX, pt, and pth, plus model roles: LLM, diffusion checkpoint/UNet, LoRA, VAE, ControlNet, embedding, vision projector, restoration/upscaler, and unknown.

v0.1 reads bounded GGUF/safetensors metadata. Other extensions are cataloged as unverified unless a safe parser is added. Never use pickle/`torch.load` to inspect untrusted checkpoints. Filename guesses remain labeled inferred. A file extension alone does not prove architecture, task support, or engine compatibility.

Record display name, locations, format, role, architecture, quantization, byte size, parameter/context metadata when known, capabilities with evidence, compatibility status, favorites, missing/changed state, hashes, and usage. Multipart models and auxiliary files are grouped as a model bundle; a partial bundle cannot be declared runnable.

### 10.2 No-duplicate policy

1. Existing files stay where they are and are registered in place.
2. New managed downloads eventually go into `~/OXIMORON/models/` by default.
3. Prefer engine-supported extra model directories; use recorded symlinks only where needed and supported.
4. Group aliases of the same underlying file using resolved path and file identity. Matching name/size is not proof of identical content.
5. Hash in the background when needed; only a complete content hash establishes byte identity across distinct files.
6. Existing duplicates are reported, never automatically deleted. Any cleanup is a separate previewed operation.
7. No format conversion/import/copy is silent. If an engine cannot reuse a file, explain the limitation or require an explicit storage-expanding action.
8. Removing a model from the registry is separate from deleting its bytes. External files are never deleted as a side effect of unregistering an engine.

### 10.3 Data layout

| Data | Default Linux location | Notes |
| --- | --- | --- |
| YAML config | `$XDG_CONFIG_HOME/oximoron/config.yaml`, fallback `~/.config/oximoron/config.yaml` | No secret values |
| SQLite | `$XDG_DATA_HOME/oximoron/oximoron.db`, fallback `~/.local/share/oximoron/oximoron.db` | Local disk; versioned schema |
| Logs/state | `$XDG_STATE_HOME/oximoron/`, fallback `~/.local/state/oximoron/` | Rotation, ownership records, redaction |
| Runtime lock/discovery | `$XDG_RUNTIME_DIR/oximoron/`, fallback private per-user runtime directory | Mode 0700 directory, 0600 files; validated owner |
| Caches/thumbnails | `$XDG_CACHE_HOME/oximoron/`, fallback `~/.cache/oximoron/` | Regenerable; size limit |
| Managed weights | `~/OXIMORON/models/` | User-selectable; no migration on path edit |
| Generations | `~/OXIMORON/generations/YYYY/MM/DD/` | Date folder from local creation date; timestamps stored in UTC |
| Attachments | OXIMORON data directory under `attachments/` | User-imported, size/type validated |

All paths resolve through a platform-path service. Windows locations use platform conventions when support is implemented. Never write user data into the application bundle or repository.

## 11. Routing and orchestration

Supported intent vocabulary: CHAT, CODING, IMAGE_GENERATION, IMAGE_EDIT, IMAGE_UPSCALE, VISION, MODEL_LAUNCH, MODEL_DOWNLOAD, ENGINE_CONTROL, FILE_OPERATION, SYSTEM_OPERATION, TOOL_CALL.

v0.1 dispatches explicit UI/API tasks only. v0.2 deterministic routing considers explicit UI mode, selected engine/provider/model, structured commands, attachments, and narrow phrase patterns. Quoted examples and discussions of image generation must not trigger generation. Requests for file/system/tool operations produce a proposed action requiring the appropriate permission path; they do not execute from text alone.

Ambiguity defaults to chat or asks the user. A tiny local classifier may be introduced after a representative routing dataset demonstrates a benefit and its memory/latency overhead is measured. Classifier output is untrusted and cannot grant permission or bypass locality.

Orchestration sequence: validate request → resolve policy → classify/select → verify capability/model assets → establish job/idempotency → obtain approval if needed → reserve resources → prepare/start engine → verify readiness/load → execute → stream events → persist result → release reservation → record usage → schedule idle policy/offer restoration.

Any wait for user input releases transient resource reservations; on approval, recompute admission. Cancellation, failures, and process death must release locks/reservations exactly once. Do not keep database transactions open across inference or approval waits.

## 12. Resource management

v0.1 displays telemetry and conservatively serializes managed GPU-heavy jobs. It rejects unsafe conflicts with a clear action; it does not automatically evict a model. CPU work may run alongside GPU work if RAM admission permits.

v0.2 estimates weights + KV cache/context + compute buffers + image working memory + safety reserve, using adapter-specific formulas and measured peaks where available. Model file size is not VRAM demand. Recommendations include range, evidence, confidence, context/resolution, and last measurement.

Automatic reclamation requires all of: user-enabled policy, verified owned process, idle/no active leases, supported unload/stop operation, and a fresh recheck immediately before acting. Never unload an in-flight chat, generation, external process, or externally attached engine automatically.

Idle duration is measured since the last active request completes, not since the last UI click or health check. Options: never, 5, 10, 30 minutes; v0.2 default 10 minutes once automatic management is explicitly enabled. Polling does not reset the timer. Unknown or stale metrics prevent automatic optimistic overcommit.

For llama.cpp builds without a validated unload route, unloading means stopping the owned server and remembering its launch spec. For image engines, idle UI state does not prove memory is released; verify metrics after unload or stop.

## 13. Chat, cloud, and images

Chat supports sanitized Markdown, inert code blocks, streaming, system prompt and sampling settings, context budgeting, saved partial responses, errors and cancellation. Attachments/vision are enabled only for compatible model/adapter combinations. A model's advertised context length is distinct from the configured runtime limit.

Provider adapters normalize capabilities and messages, not pretend every provider supports the same options. Planned providers: OpenAI, Gemini, Anthropic, OpenRouter, and explicitly registered OpenAI-compatible endpoints. Credentials live in the OS keyring; the DB stores references. Provider identity, exact API model ID, endpoint, timeout, rate limits, and allowed data policy are explicit. Provider-specific endpoint selection is verified during implementation.

No automatic cloud retry after a response starts or an outcome becomes ambiguous. Transient retries before dispatch are bounded; 429 handling respects server hints and shared provider/account cooldowns. No key cycling or proxy changes to evade limits. Cost estimates, where available, are labeled estimates and never required for local operation.

Image Studio persists requested and effective settings, prompt/negative prompt, model identity/hash when available, LoRAs and weights, seed, sampler, steps, CFG, dimensions, engine/version, workflow version, duration, outputs, and failure/partial status. Unknown engine-returned values remain unknown. A returned image must be written durably before reporting a successful saved artifact.

The simple/advanced/workflow preference eventually maps to Fooocus/Forge/ComfyUI only when the selected adapter actually supports the requested task/model. In v0.1 all integrated image generation uses Forge. Reuse settings is deterministic configuration restoration; exact pixels are not guaranteed across software/hardware versions.

## 14. Workspaces, tools, MCP, and plugins

Workspaces are named policy/preset bundles: preferred engines/models, prompt defaults, generation defaults, allowed filesystem roots, tool grants, and cloud policy. Photography and Development are editable templates. Private is a policy template with cloud disabled. Workspace changes apply to new jobs; active jobs retain a versioned policy snapshot.

| Template | Initial preset | Selection behavior |
| --- | --- | --- |
| Photography | Local chat + Forge; 1024 × 1024 image preset; optional portrait/cinematic LoRAs; EXIF/image-analysis tools when implemented | User selects installed compatible checkpoint/LoRAs; names in the brief are examples, not bundled models |
| Development | Preferred coding model; requested 32,768-token context; Files/Git/Terminal/MCP when implemented | Validate actual context support and RAM/VRAM; unavailable tools stay disabled |
| Private | Local chat/images; no cloud or remote tools/catalogs; telemetry off | Missing local capability produces an explanation, never a remote fallback |

Tool execution first arrives in v0.4. Every call has a typed schema, workspace scope, risk classification, preview, cancellation/deadline, bounded output, and audit trail. “Read-only command” is not assumed from the executable name: Git configuration, hooks, shell expansion, Python, and browser navigation can have side effects.

Permission choices: allow once, allow a precisely scoped action for this workspace, deny. Writes/deletes/privileged operations require explicit approval under policy. General terminal/Python execution cannot receive a broad permanent safe grant. No unattended root/sudo. Model output, retrieved documents, and MCP descriptions are untrusted inputs.

MCP is a tool connector type, with local process/remote transport identity, workspace enablement, health, timeouts, protocol compatibility, and tool schema validation. Connected does not imply authorized. Remote servers are unavailable under Private policy.

Plugin types: engine, provider, tool, model_source, and later UI. A versioned manifest declares capabilities, permissions, entrypoint, supported host API, and provenance. v0.1 uses built-in adapters behind these boundaries; it does not import arbitrary plugins. v1.0 introduces isolated plugin processes where practical, installation review, permission revocation, and compatibility checks. Schema validation and signatures do not prove a plugin is safe. UI plugins require an isolated surface and are not injected into the privileged desktop renderer.

## 15. Local API, CLI, and desktop lifecycle

Canonical control API: `http://127.0.0.1:6969/api/v1`. Compatibility API later exposes `/v1/chat/completions`, `/v1/models`, and `/v1/embeddings` only for implemented capabilities. Bare routes from the concept, such as `/chat`, are conceptual names; do not maintain a second unversioned contract.

CLI experience:

```text
oximoron serve
oximoron status
oximoron engines list
oximoron engines start forge
oximoron engines stop llamacpp
oximoron run <registered-model-id-or-unique-alias>
oximoron ask "Explain PCA"
oximoron generate "cat driving a WagonR"
oximoron logs forge
```

`oximoron forge start` may be a convenience alias for the canonical engine command. Ambiguous model names produce a selection/error, never a guess. `--json` provides structured output; noninteractive commands fail clearly when approval is required. CLI cancellation targets its job, not the backend process.

v0.2 tray displays owned engine states and sampled GPU use; actions use the API. Explicit Exit differs from Hide Window. Autostart is opt-in; restore previous UI session does not imply launching expensive engines or replaying jobs. If the tray is unavailable, use a visible window/minimize behavior and explain it.

## 16. Security and privacy model

Threats in scope: malicious web pages contacting localhost, leaked API keys, hostile model metadata/files, injected prompts, unsafe plugin/tool output, accidental process termination, broad filesystem writes, and unintended cloud disclosure.

- Authenticate all control and data endpoints. Loopback binding and CORS are insufficient alone.
- Validate Host and Origin; use exact allowed origins; do not use wildcard CORS with credentials. Apply CSP and render generated content without executable HTML.
- Bootstrap desktop credentials over a controlled native channel; keep them out of URLs, logs, localStorage, and child-engine environments.
- WebSocket authentication uses a short-lived one-use ticket obtained through the authenticated API; do not put the long-lived API token in the query string.
- Treat model/settings/attachment paths as untrusted. Canonicalize, scope, validate file type/size, and recheck before writes.
- Launch with argument arrays, known working directories, and a minimized environment. A prompt is never interpolated into a shell command.
- Keep provider keys out of DB/YAML/export/logs/process arguments. Missing/locked keyring disables stored-secret operations; there is no plaintext fallback.
- Engine configuration cannot enable public listening or remote share/tunnel options by default. Locality checks include endpoint host and redirects.
- Logs avoid prompt bodies by default; redact credentials, authorization headers, and URLs with secrets. Export previews warn that engine output can still contain user content.
- No telemetry/upload/crash reporting by default. Any future export or report is deliberate and previewable.
- Third-party installed code is a trust boundary. OXIMORON prevents accidental actions but does not claim to defeat a compromised same-user process.

API remote access in v1.0 is a separate mode requiring explicit configuration, TLS, scoped credentials, stronger identity/access controls, rate limits, and a deployment threat review. Changing a bind host alone does not qualify as remote support.

## 17. Persistence, configuration, and recovery

SQLite holds entities and history; YAML holds operational configuration. A field has one authoritative store. Workspace presets and entity records belong in SQLite; engine executable paths/launch settings and global operational options belong in YAML. The database engine row references the config ID and records runtime/compatibility facts.

Use foreign keys, migrations, bounded write transactions, a busy timeout, and WAL on local disk. WAL still permits only one writer at a time and has filesystem constraints; it is not a substitute for transaction design. Use SQLite's backup mechanism for live backups. [SQLite WAL documentation](https://sqlite.org/wal.html)

State recovery distinguishes: a failed job, an interrupted job, an ambiguous external completion, and a successfully saved result. After backend restart, do not automatically reissue inference. Reconcile verified processes, mark interrupted work, and offer explicit retry.

YAML updates use schema validation, version/revision checks, write-to-temp plus atomic replacement, and a last-known-good backup. Invalid edits surface diagnostics and preserve the previous usable configuration. Migrations create a verified backup and fail closed if the schema is newer than the app understands.

Defaults: rotate logs at 10 MiB × 5 files per source with a 250 MiB global cap; retain terminal job/event diagnostics for 30 days; cap thumbnails at 512 MiB. Never automatically delete model weights, conversations, or generated originals. These are initial design values to validate, not measured storage needs.

## 18. Reliability and performance targets

| Area | Initial target | Measurement |
| --- | --- | --- |
| Idle CPU | <1% average of one core after warm-up | Five-minute idle sample, no engines/tasks |
| Manager memory | 150–300 MiB target; investigate >400 MiB | Combined backend/host/webview memory, accounting for shared pages |
| GPU | No manager inference allocation; compositor overhead reported separately | NVML process/device samples where supported |
| Warm dashboard | Usable within 2 seconds | Packaged app on reference machine |
| Cold launch | Usable within 5 seconds excluding engine launch | No network and no initial full model hash scan |
| Telemetry | 1-second visible samples, 5-second background samples | UI event loop remains responsive |
| Discovery | Incremental/cancellable, results visible as found | Large selected directory fixture |
| Chat display | Render streamed chunks within 100 ms of receipt under normal load | Frontend streaming benchmark |
| Cancellation | Acknowledged by manager within 1 second | Engine cessation tracked separately |
| Logs/events | Bounded queues, no unbounded memory growth | Flood and slow-consumer tests |

These are budgets to measure, not promises already achieved. End-to-end inference speed depends on the engine/model/hardware and must be reported separately from manager overhead.

## 19. Risks and planned decisions

| Risk | Mitigation | Decision/release gate |
| --- | --- | --- |
| Python sidecar packaging increases memory/startup or misses native libraries | Package a minimal backend early; test clean host | M00/M01 feasibility and M12 release gate |
| Adapter API/flags drift | Capture installed version/help/schema; contract fixtures; tested version matrix | Every adapter change |
| Fooocus lacks a suitable stable integration for selected version | Lifecycle support remains useful; bridge is optional and explicit | M17, never block Forge MVP |
| VRAM estimates are inaccurate | Ranges, safety reserve, single GPU queue, measured peaks, clear OOM diagnostics | M08/M14 hardware runs |
| Orphan processes or PID reuse | Persistent identity records, ownership rechecks, no blind kill | M04/M12 fault tests |
| Existing files/configs are damaged | Register in place; preview/backup reversible writes | M06/M17 filesystem tests |
| Unknown checkpoint runs code during inspection | Safe metadata only; no executable deserialization | Scanner security gate |
| Local API exposed to malicious pages | Authentication + Host/Origin validation + desktop CSP | M02/M11 security gate |
| Duplicate weights through downloader/import | Content/location registry; no implicit copy; explicit import limitations | M17 storage audit |
| Feature expansion delays first useful release | v0.1 gate before cloud/tools/plugins | Every milestone review |
| Tray, GPU, keyring, or webview differs by distro | Degraded modes and actual supported-platform smoke tests | Packaging release matrix |

## 20. Delivery order and effort assumptions

Dependency-driven order: contracts/feasibility → Tauri shell → FastAPI/auth/persistence → process manager → llama.cpp → model registry → Forge → telemetry/admission → usable chat/create → CLI/integration → packaged v0.1 → deterministic routing/history/cloud → automatic resources/workspaces → workstation integrations → tools/MCP → ecosystem.

A small read-only telemetry slice is developed before full resource management so the first release can display useful hardware status. Security, persistence, and capability checks accompany each slice.

For one experienced full-time developer, a planning allowance is roughly 10–15 focused development weeks for a qualified v0.1; v0.2 another 6–10; v0.3 another 8–12; v0.4 another 8–12; v1.0 platform qualification/extensibility another 10–16. These are rough allowances including integration/debugging, not calendar commitments. Hardware availability and engine compatibility can dominate. Re-estimate after M00 and after real llama.cpp/Forge runs; prioritize the acceptance gate over dates.

No user choice blocks the current planning deliverable. Implementation defaults are Linux-first, existing engines/models, built-in adapters, no telemetry, Forge for integrated images, and no cloud enabled initially. Repository license, public distribution branding, engine redistribution rights, signing identities, remote deployment model, and exact compatibility version pins must be settled at their corresponding release gates; do not guess them.

## 21. Traceability to the complete brief

Every numbered concept from the brief is assigned below. “Foundation” means its boundaries are designed early, not that its final UX is complete.

| Brief items | Requirement | Planned delivery / implementation work |
| --- | --- | --- |
| 1–2 | Unified control center and command interface | v0.1 M01–M12 |
| 3–4 | Four modes and deterministic router | Explicit dispatch v0.1; full modes/router v0.2 M13 |
| 5–7 | Engine abstraction, discovery, dashboard | v0.1 M03–M07/M11 |
| 8 | Owned process manager | v0.1 M04; recovery enhancements M14 |
| 9–10 | Model scan and registry | v0.1 M06; enriched metadata M14/M17 |
| 11 | No duplicate models | Register-in-place v0.1; shared-path/symlink workflows M17 |
| 12 | Model downloads | v0.3 M17 |
| 13–15 | Recommendations, VRAM manager, idle unloading | Monitoring/admission M08; automatic behavior M14 |
| 16 | Chat | v0.1 M09; vision/rich history M13–M15 |
| 17–18 | Cloud abstraction and API compatibility | v0.2 M15; compatible facade M16 |
| 19–22 | Studio, engine selection, gallery, editing | Forge M10; routing M13; advanced studio M18 |
| 23 | Workspaces | v0.2 M16 |
| 24–26 | Tools, permissions, MCP | Security foundations M02; tool execution v0.4 M19–M20 |
| 27 | Plugins | Built-in interface foundations M03; SDK/marketplace architecture M21 |
| 28–29 | Local API and CLI | v0.1 M02/M11; compatibility facade M16 |
| 30–31 | Tray and startup settings | v0.2 M16 |
| 32 | Central logs | v0.1 M04/M11 |
| 33–34 | Crash recovery and ports | Basic correctness M04/M12; recovery UI M14 |
| 35–36 | YAML and SQLite | v0.1 M02 |
| 37–40 | Repository, stack, services, orchestrator | M00–M03; extended in each phase |
| 41–45 | Pages, home, palette, search, theme | Shell M01; usable UI M09–M11; search M16 |
| 46–50 | v0.1 through v1.0 | Milestone gates M12/M16/M18/M20/M22 |
| 51–53 | Offline, security, low overhead | Cross-cutting, verified at every gate |
| 54 | Restore prior hardware/model environment | v0.2 M14 |
| 55–56 | Task-based loading and profiles | v0.2 M13/M16 |
| 57 | Universal capability API | Versioned API foundation M02; full facade/SDK M16/M21 |

## 22. Planning handoff checklist

- [x] Product, scope, releases, boundaries, and all 57 brief items mapped.
- [x] Architecture, service ownership, UX flows, resource policy, storage, and security defined.
- [x] Technical contracts, schemas, ordered tasks, and verification defined in `implementation.md`.
- [x] Contributor/agent operating rules defined in `agent.md`.
- [ ] Implementation explicitly requested by the user.
- [ ] M00 compatibility and packaging investigation completed.
- [ ] Any application feature built or validated.
