# OXIMORON — Implementation Specification and Delivery Backlog

Status: proposed implementation; every milestone is **not started**.
Baseline: 2026-09-22. Companion documents: [plan.md](plan.md), [agent.md](agent.md).

This document specifies future work. It does not authorize executing it during the current planning-only task. Examples are contract proposals, not installed commands or implemented APIs.

Quick navigation: [repository](#2-proposed-repository-layout) · [contracts](#3-core-contracts) · [state machines](#4-state-machines) · [API](#5-api-specification) · [database](#6-persistence-schema) · [configuration](#7-configuration-specification) · [algorithms](#8-critical-algorithms-and-failure-behavior) · [M00–M22 backlog](#10-delivery-work-packages) · [verification](#12-test-strategy).

## 1. Execution rules and completion model

Build vertical slices: usable UI → authenticated request → orchestrator → real adapter → persisted result → visible error/recovery. Do not build an entire plugin platform before local chat works.

A work package is complete only when its listed deliverables and acceptance checks pass. Record exact commands, environment, engine versions, results, and remaining gaps. “Implemented,” “automatically tested,” “tested with a real engine,” and “packaged desktop verified” are different evidence levels.

Use these status values during future work: `not_started`, `in_progress`, `blocked`, `ready_for_validation`, `done`. A blocked hardware test does not turn a milestone into done. There are no committed completion dates in this document.

## 2. Proposed repository layout

```text
oximoron/
  plan.md
  agent.md
  implementation.md
  README.md                       # created during implementation
  pyproject.toml                  # Python package/tool configuration
  uv.lock
  package.json                    # workspace tasks only
  pnpm-workspace.yaml
  pnpm-lock.yaml
  apps/
    desktop/
      src/
        app/                      # routes, providers, layout
        components/               # accessible shared primitives
        features/                 # home/chat/create/models/engines/etc.
        lib/                      # typed API, stream/event transport
        styles/                   # tokens, base styles
      src-tauri/                  # Rust bootstrap, native capabilities
      package.json
      vite.config.ts
    backend/
      main.py                     # app factory; no startup side effects on import
      api/v1/                     # thin HTTP routers and WebSocket endpoint
      dependencies.py
      lifespan.py                 # supervisor/service startup/shutdown
    cli/
      main.py
      client.py
  core/
    contracts/                    # Pydantic DTOs, enums, errors, protocols
    orchestrator/
    router/
    process_manager/
    resource_manager/
    model_registry/
    permissions/
    jobs/
    services/                     # chat, generation, engine, workspace, etc.
    persistence/                  # repositories, transactions, migrations
    config/
    secrets/
    events/
    logging/
  engines/
    base/
    llamacpp/
    forge/
    fooocus/
    comfyui/                      # created when scheduled
    ollama/                       # created when scheduled
  providers/
    base/
    openai/
    gemini/
    anthropic/
    openrouter/
    compatible/
  tools/
    base/
    filesystem/
    terminal/
    git/
    python/
    browser/
    mcp/
  shared/
    generated/                    # generated OpenAPI TypeScript client/types
    fixtures/                     # bounded, synthetic contract fixtures
  tests/
    unit/
    contract/
    integration/
    e2e/
    hardware/
    fixtures/
  scripts/                        # reproducible dev/package/verification helpers
  docs/
    adr/                          # decisions and superseding rationale
    compatibility/                # tested engine/platform matrix
    runbooks/                     # setup, recovery, release, troubleshooting
```

Create only directories needed by the active milestone. Python namespaces/package discovery must be configured deliberately in M00; do not rely on editing `sys.path` or an accidental working directory. Domain modules must not import frontend, transport, or concrete adapter modules. Composition happens in the backend bootstrap.

## 3. Core contracts

### 3.1 Common types and invariants

- IDs: generated UUIDs; engine adapter key and user-facing alias are separate from an engine-instance ID.
- Timestamps: timezone-aware UTC ISO 8601 externally, normalized UTC in storage. Use a monotonic clock for deadlines/idle timers.
- Sizes: integer bytes internally; UI labels distinguish GB from GiB. GPU utilization is nullable percent, not a default zero.
- Paths: canonical absolute paths internally plus original display path. A frontend path string does not itself authorize filesystem access.
- Every mutating request receives a request ID; long-running operations also get a durable job ID.
- User-facing errors have a stable code, safe explanation, retryability, and an optional action. Raw traces stay in redacted local diagnostics.
- Pydantic contracts generate OpenAPI/TypeScript types. Do not separately hand-maintain conflicting DTOs.
- Capability descriptors include support level: `supported`, `unsupported`, `unknown`, or `experimental`, plus evidence/version and limitations.

### 3.2 Adapter interface

| Operation | Input | Output | Ownership/side-effect rule |
| --- | --- | --- | --- |
| `detect` | Bounded approved search roots | Engine candidates + evidence | Read-only; no executing discovered code |
| `validate` | Registered candidate/config | Validated launch/API spec + issues | Approved executable may be queried for help/version with timeout |
| `capabilities` | Installation/build + optional health probe | Versioned descriptor | No inference, download, or implicit model load |
| `plan_install` | Version/platform/destination | Steps, sources, disk/network requirements | Descriptive only in v0.1 |
| `install` | Approved installation plan | Installation result | Unsupported in v0.1; isolated environment later |
| `build_launch_spec` | Validated config/model/port | Argument array, cwd, allowed env, readiness policy | Pure construction; no shell string |
| `start` | Launch spec + ownership context | Managed process handle | Delegates spawning to process manager |
| `stop` / `restart` | Verified handle + timeout | Termination/restart result | Only owned processes; identity recheck |
| `health` | Validated endpoint | Health status, loaded model, API capabilities | Readiness not inferred from TCP alone |
| `load_model` | Registry ID + validated options | Load result | May require restart; report disruption before acting |
| `unload_model` | Lease-free model session | Unload result + remaining process state | May stop owned server; verify actual release |
| `chat` | Normalized messages/options/cancel handle | Async normalized deltas + terminal result | Only when capability/model policy allows |
| `generate_image` | Normalized generation request | Progress + output descriptors | Does not invent unsupported options |
| `cancel` | Engine request identity | Cancel acknowledged/unsupported/unknown | Do not interrupt unrelated external jobs |

`EngineCapabilities` includes task names, accepted model formats/architectures, streaming/vision/tools/embeddings support, concurrency, load/unload semantics, cancel scope, external-attach support, required auxiliary files, and supported generation options.

`LaunchSpec` includes executable, argument vector, working directory, sanitized environment references, requested port, model bundle IDs, device preference, ready probe, startup deadline, graceful-stop method, and adapter/build version. It contains no cloud credentials and is fingerprinted after secret redaction where necessary.

Provider contract: `capabilities`, `validate_configuration`, `list_models` when supported, and `generate(messages, options, cancel)` returning normalized events. Providers never manage local engine processes. Tool contract: `describe`, `validate`, `plan`, `execute`, `cancel`; plan and execute are separated by policy/approval.

### 3.3 Request and routing contract

Illustrative resolved route:

```json
{
  "intent": "IMAGE_GENERATION",
  "engine_instance_id": "configured-forge-instance-id",
  "model_id": "registered-checkpoint-id",
  "requires_gpu": true,
  "locality": "local",
  "confidence": "explicit",
  "reason_code": "create_workspace_selected",
  "policy_revision": 7,
  "required_permissions": [],
  "unsupported_options": []
}
```

Example IDs above are explanatory; actual API IDs use UUID validation. Intent detection and executable action generation are different steps. A route may return `needs_selection` or `permission_required` instead of an executable engine target.

`ChatRequest`: conversation ID or new-conversation spec, ordered messages or a new user message according to endpoint, selected mode/workspace/model/provider, system prompt, sampling settings, context policy, attachment IDs, and stream preference. Do not accept both a persisted history ID and an uncontrolled replacement history without explicit semantics.

For the canonical conversation endpoint, the client submits a new user message plus conversation ID; the backend constructs history. For the compatibility endpoint, the client supplies the full message array and storage is opt-in. This prevents duplicate messages and accidental hidden context.

`ImageRequest`: workspace ID, prompt, negative prompt, engine/model IDs, LoRA references/weights, dimensions, steps, CFG, sampler/scheduler, seed or random, batch count, output format, and later input artifact/mask/workflow references. Versioned validation rejects options that the chosen adapter cannot honor.

## 4. State machines

### 4.1 Engine state

```text
unconfigured -> configured -> stopped -> starting -> loading -> ready <-> busy
                                              |                 |
                                              +---- failed <----+
ready/busy -> stopping -> stopped
ready/busy -> degraded -> ready OR failed
external_detected -> attached_external   (separate ownership, explicit attach)
```

An API-only external engine may have no owned PID. “Installed,” “process running,” “API ready,” and “model loaded” are separate fields; the state machine is a summary, not a substitute for those facts.

Transitions are guarded by an engine-instance lock and persisted with a revision. Duplicate starts return the active start job. Stop during start cancels startup, then cleans up only the spawned owned process group. Restart is stop-complete followed by start under the same serialized control operation.

### 4.2 Job state

```text
queued -> planning -> waiting_permission -> queued
                  -> waiting_resources -> preparing -> running -> persisting -> succeeded
any nonterminal state -> cancel_requested -> cancelled
any nonterminal state -> failed
backend loss -> interrupted OR outcome_unknown after reconciliation
```

`waiting_permission` and `waiting_resources` have deadlines. `cancel_requested` is not equivalent to cancelled. Terminal states are immutable except for an audited reconciliation of `outcome_unknown` when a verified output is discovered. Retrying creates a new job linked to the old one.

Engine completion may race cancellation. If a valid output was already produced, persist it and expose `completed_after_cancel_request`; do not discard useful output or claim cancellation prevented execution. Transport disconnection alone does not cancel an image job.

Chat disconnection uses a brief reconnect grace period, proposed 10 seconds, then cancels by default if no client reattaches. Backend-owned image jobs continue through UI disconnect and are recovered via job events/history. Application exit uses an explicit cancel/drain policy.

### 4.3 Download state, introduced in v0.3

`queued → resolving → downloading → verifying → committing → completed`, with `paused`, `cancel_requested`, `cancelled`, and `failed`. A partial file is never registered as a usable model. Restart resumes only if source identity and HTTP resume validators still match.

## 5. API specification

### 5.1 Transport and authentication

Base URL: `http://127.0.0.1:6969/api/v1`, with actual endpoint discoverable from a protected runtime record when a port changes. Authentication: per-installation/local-user random API secret held in an OS keyring when available, otherwise in an owner-only runtime credential file for the active backend session. This fallback applies only to the local API bootstrap credential, never cloud provider keys. Rotate on explicit reset; session-only secrets expire with the supervisor.

The runtime record stores endpoint, supervisor instance ID, process identity, protocol version, and credential reference. Validate owner/mode and backend identity before sending the token. Desktop receives the credential through native bootstrap IPC; CLI reads the protected credential reference. No token in command-line arguments, browser storage, URLs, ordinary logs, or inherited engine environment.

Before credential delivery, verify the live supervisor's creation/executable identity and OS listener ownership against the protected record. A matching port or unauthenticated product-name response is insufficient. If identity cannot be established, refuse attachment and provide diagnostics. Local control clients disable HTTP redirects so credentials cannot follow a changed endpoint. Same-user malware is outside the isolation guarantee.

All HTTP data/control routes require a Bearer token. Desktop request origins are pinned to actual packaged Tauri origins per platform, plus an explicit development origin during development. Native CLI requests without Origin still require auth and a valid Host. No arbitrary web origin, null-origin allowance, or reflected CORS.

WebSocket: authenticated POST creates a one-use ticket with a 30-second TTL. Client sends it as the first message; until validated, server sends no data and accepts no commands, with a 5-second timeout. Validate Origin and bound unauthenticated connections. Tickets and message bodies are redacted from logs.

### 5.2 Canonical endpoints

All routes below are under `/api/v1` unless stated otherwise. P0 = v0.1; P1 = v0.2; P2 = v0.3; P3 = v0.4; P4 = v1.0.

| Method and path | Purpose | Release |
| --- | --- | --- |
| GET `/health` | Authenticated backend readiness, schema/protocol version, subsystem status | P0 |
| GET `/status` | Compact system/engine/job summary for Home/CLI | P0 |
| GET `/system` | Timestamped CPU/RAM/disks/GPU snapshot and availability | P0 |
| GET `/system/gpu` | GPU-specific view of the same hardware snapshot | P0 |
| POST `/engines/discover` | Bounded discovery job for configured/selected roots | P0 |
| GET/POST `/engines` | List/register engine instances | P0 |
| GET/PATCH `/engines/{id}` | Detail/configuration update with revision validation | P0 |
| POST `/engines/{id}/start` | Idempotent start job | P0 |
| POST `/engines/{id}/stop` | Owned stop job; busy handling explicit | P0 |
| POST `/engines/{id}/restart` | Serialized owned restart job | P0 |
| GET `/engines/{id}/health` | Cached/probed engine health without implicit launch | P0 |
| POST `/engines/{id}/attach` | Explicit external endpoint attachment | P1 |
| GET `/processes` | Owned/reconciled process inventory; redacted launch details | P0 |
| GET `/models` | Paginated/filterable registry | P0 |
| POST `/models/scan` | Cancellable scan of registered roots | P0 |
| GET/PATCH `/models/{id}` | Details/favorite/display metadata | P0 |
| POST `/models/{id}/load` | Explicit engine/model preparation job | P0 |
| POST `/models/{id}/unload` | Release owned model session or report unsupported | P0 |
| GET/POST `/conversations` | List/create local conversation records | P0 |
| GET `/conversations/{id}` | Conversation and paginated messages | P0 |
| POST `/chat` | Submit user message; SSE stream or job response | P0 |
| POST `/generate/image` | Submit local generation; return job immediately | P0 |
| GET `/generations` | Paginated saved generation metadata | P0 |
| GET `/generations/{id}` | Effective settings, outputs, provenance | P0 |
| GET `/artifacts/{id}/content` | Authorized artifact bytes; bounded supported types | P0 |
| POST `/attachments` | Validated local attachment import | P1 |
| GET `/jobs` and `/jobs/{id}` | Paginated jobs and durable job snapshots | P0 |
| GET `/jobs/{id}/events` | SSE stream/replay of bounded durable job events | P0 |
| POST `/jobs/{id}/cancel` | Idempotent cancellation request | P0 |
| GET `/logs` | Bounded, filtered, cursor-based redacted logs | P0 |
| GET/PUT `/settings` | Read/validate/update operational settings with revision | P0 |
| POST `/events/ticket` and WS `/events` | Authenticated shared status/progress stream | P0 |
| POST `/routes/preview` | Explain policy/intent/engine choice without execution | P1 |
| GET/POST/PATCH `/providers[/{id}]` | Provider registration and nonsecret settings | P1 |
| PUT/DELETE `/providers/{id}/credential` | Store/remove keyring credential; never return key | P1 |
| POST `/providers/{id}/test` | Explicit small capability/auth test; possible cost disclosed | P1 |
| GET/POST/PATCH `/workspaces[/{id}]` | Workspace presets and policy revisions | P1 |
| GET `/search` | Workspace-scoped local grouped search | P1 |
| POST `/environment/restore` | Restore an explicit saved environment snapshot | P1 |
| GET `/model-sources/search` | Explicit online catalog search | P2 |
| POST `/engines/install/plan` and `/engines/install/apply` | Preview/apply a supported user-approved installation recipe | P2 |
| GET/POST `/downloads` | List/queue downloads | P2 |
| POST `/downloads/{id}/{pause,resume,cancel}` | Download lifecycle actions | P2 |
| POST `/models/{id}/links/plan` and `/models/{id}/links/apply` | Preview/apply approved shared-path/symlink plan | P2 |
| POST `/generate/{edit,upscale}` | Capability-checked image operations | P2 |
| GET `/tools` and POST `/tools/{id}/plan` | Discover scoped tools and preview a call | P3 |
| POST `/tools/{id}/execute` | Execute through permission service | P3 |
| GET `/permissions/pending` | User approval queue | P3; resource approvals use same primitive in P1 |
| POST `/permissions/{id}/decision` | Bound, expiring approval or denial | P1 primitive/P3 tools |
| GET/POST `/mcp/servers` | Manage validated MCP connector configurations | P3 |
| GET/POST `/plugins` | Reviewed plugin registry/install workflow | P4 |

Bracketed path notation summarizes multiple concrete routes; it is not literal OpenAPI syntax. Freeze each concrete route in its implementing milestone. Do not expose unimplemented future endpoints with fake success responses.

Compatibility routes, outside the prefix, arrive in M16: GET `/v1/models`, POST `/v1/chat/completions`, POST `/v1/embeddings` when supported. They use the same authentication/policy/orchestrator. A list entry means configured/discoverable, with readiness communicated through canonical metadata; it must not imply that every advertised model can run now.

### 5.3 Commands, idempotency, and errors

Long operations return HTTP 202 with job ID, initial state, and event/status URLs. Fast validated reads return 200; synchronous creates return 201. Input errors: 422. No credentials: 401. Policy denial: 403. Unknown entity: 404. Conflict/busy/stale revision: 409. Rate limit: 429. Unavailable backend/capability preparation: 503. Unknown internal error: 500 with safe message.

Typed error body:

```json
{
  "error": {
    "code": "RESOURCE_CONFLICT",
    "message": "The selected engine needs memory currently held by an owned chat engine.",
    "request_id": "request-uuid",
    "retryable": false,
    "action": "review_resource_plan",
    "details": {"resource_plan_id": "plan-uuid"}
  }
}
```

Required codes include `ENGINE_NOT_CONFIGURED`, `ENGINE_UNSUPPORTED`, `ENGINE_START_FAILED`, `ENGINE_NOT_READY`, `ENGINE_BUSY`, `PROCESS_IDENTITY_MISMATCH`, `PORT_CONFLICT`, `MODEL_MISSING`, `MODEL_INCOMPATIBLE`, `RESOURCE_CONFLICT`, `GPU_METRICS_UNAVAILABLE`, `OFFLINE_POLICY`, `KEYRING_UNAVAILABLE`, `PROVIDER_RATE_LIMITED`, `PERMISSION_REQUIRED`, `PERMISSION_DENIED`, `INVALID_CONFIG`, `DISK_FULL`, `CANCEL_UNSUPPORTED`, `OUTCOME_UNKNOWN`, and `EVENT_CURSOR_EXPIRED`.

`Idempotency-Key` is required for retryable client submissions of inference and engine commands. Store key + operation + workspace/client scope + payload hash + job result reference for at least 24 hours. Reuse with the same payload returns the same job; changed payload returns 409. This prevents duplicate local dispatch, but cannot guarantee exactly-once execution against third-party APIs after crashes. Uncertain remote outcomes are explicitly marked.

### 5.4 Streaming and events

Event envelope: `schema_version`, `event_id`, `supervisor_instance_id`, `sequence`, `job_id` if applicable, `entity_id`, `type`, `timestamp`, `payload`. Durable job events have a per-job sequence; volatile telemetry has its own stream sequence.

Event families: `job.state`, `route.selected`, `approval.required`, `resource.waiting`, `engine.state`, `model.loaded`, `chat.delta`, `chat.completed`, `generation.progress`, `generation.saved`, `download.progress`, `system.snapshot`, `log.line`, `error`, and `resync_required`.

Persist job transitions and terminal outcomes. Batch chat text persistence (proposed every 1 second or 4 KiB, and on terminal state) rather than one DB transaction per token. Reconnect retrieves job/message snapshots then resumes available events; UI deduplicates by sequence. This permits losing a small unflushed tail on a hard crash, which must be documented as partial content.

Use bounded per-client queues. Coalesce telemetry/progress, trim log tails, and force a slow chat consumer to reconnect from persisted text rather than buffering indefinitely. Initial proposals: 256 queued events per client, 64 KiB maximum ordinary event payload, 15-second heartbeat. Large image bytes travel through artifact routes, not WebSocket events.

## 6. Persistence schema

### 6.1 Storage conventions

Foreign keys on, migrations versioned, short transactions, indexes for filter/order paths, and local-disk WAL. Use an explicit write coordination strategy with bounded busy retries; one backend process does not eliminate concurrent coroutine writes. Never hold a DB transaction during subprocess startup, a network call, user approval, model scanning, or generation.

Mutable tables carry `created_at`, `updated_at`, and a revision where optimistic concurrency is required. JSON columns are validated/versioned structured metadata, not a place to hide relationships needed for integrity.

### 6.2 Tables and key fields

| Table | Key fields beyond common IDs/timestamps | Constraints / first use |
| --- | --- | --- |
| `models` | name, role, architecture, format, quantization, parameter_count, context_length, metadata_json, metadata_provenance, favorite, last_used_at | Unknown metadata nullable; P0 |
| `model_files` | model_id, relative_role, byte_size, full_hash, hash_algorithm, hash_state, bundle_index | Complete content hashes indexed; P0 |
| `model_locations` | model_file_id, root_id, display_path, canonical_path, device_id, inode/file_id, mtime_ns, available, managed | Canonical path uniqueness per root policy; P0 |
| `model_roots` | path, recursive, depth_limit, enabled, scan_status, last_scan_at | User-approved roots; P0 |
| `model_compatibility` | model_id, engine_adapter, engine_version, capability, status, evidence, checked_at | Unique model/engine/version/capability; P0 |
| `engines` | adapter_key, display_name, config_key, version, capability_json, observed_state, last_health_at | Config key unique; no duplicated launch-path authority; P0 |
| `processes` | engine_id, pid, create_time, boot_id when available, executable_identity, command_fingerprint, group_id, ownership, port, model_id, start_at, exit_at, exit_code, status, log_ref | One active owned lifecycle per engine instance; P0 |
| `model_sessions` | engine_id, model_id, process_id, configured_context, load_at, last_active_at, unloaded_at, device_id | Distinguishes installed versus loaded; P0 |
| `jobs` | kind, workspace_id, engine_id/provider_id, state, request_snapshot, policy_revision, parent_job_id, cancel_requested_at, started_at, finished_at, error_code, outcome_json | Versioned state transitions; P0 |
| `job_events` | job_id, sequence, event_type, payload_json, timestamp | Unique job/sequence; indexed retention; P0 |
| `idempotency_keys` | scope, operation, key_hash, payload_hash, job_id, expires_at | Unique scope/operation/key_hash; P0 |
| `conversations` | workspace_id, title, default_model_id/provider_id, system_prompt, archived_at | Default workspace exists from P0 |
| `messages` | conversation_id, sequence, role, content_json, status, job_id, model_id/provider_id, tokens_in/out, usage_source | Unique conversation/sequence; partial/error status; P0 |
| `generations` | job_id, workspace_id, engine_id, model_id, requested_settings_json, effective_settings_json, seed, duration_ms, status | One job may produce many artifact outputs; P0 |
| `artifacts` | generation_id nullable, kind, relative_path, media_type, byte_size, hash, width, height, provenance_json | Managed root only; P0 |
| `attachments` | artifact_id, original_name, import_source, validated_type, validation_state | No arbitrary executable loading; P1 |
| `workspaces` | name, preset_json, privacy_policy_json, allowed_roots_json, revision | P0 default row; full UI P1 |
| `settings` | key, value_json, schema_version | UI preferences only; operational settings remain YAML; P0 |
| `providers` | type, display_name, base_url, enabled, credential_ref, model_config_json, policy_json | No secret values; P1 |
| `resource_leases` | job_id, device_id, ram_bytes, vram_bytes, state, acquired_at, released_at | Unique active lease per job/device; reconciled on restart; P1 |
| `environment_snapshots` | workspace_id, engine_id, model_id, launch_options_json, profile, cause_job_id, expires_at | Stores configuration identity, not blindly reusable PID; P1 |
| `model_usage` | model_id, engine_id, job_id, duration_ms, peak_ram/vram, tokens, settings_fingerprint, measurement_confidence | P0 basic usage; P1 recommendation inputs |
| `downloads` | source, revision, destination, partial_path, etag, last_modified, expected_size/hash, received_bytes, state, error | Secret headers excluded; P2 |
| `model_links` | model_file_id, engine_id, target_path, link_type, prior_state_ref, manifest_revision | Records only links managed by OXIMORON; P2 |
| `tools` | tool_key, connector_id, schema_json, risk_class, capabilities, enabled | P3 |
| `permission_requests` | principal, workspace_id, action_hash, canonical_args, policy_revision, expires_at, decision, decided_at | P1 resource primitive, expanded P3 |
| `permission_grants` | workspace_id, principal, action_scope_json, expires_at, revoked_at | Narrow reusable scope only; P3 |
| `tool_calls` | job_id, tool_id, permission_id, input_redacted, output_ref, exit_status, duration | Auditable, bounded output; P3 |
| `mcp_servers` | name, transport, config_ref, version, state, enabled_workspaces | Credentials by reference; P3 |
| `plugins` | manifest_json, source, version, integrity, install_path, enabled, granted_permissions | Schema and compatibility validated; P4 |

Use migrations to add later-release tables when needed, not all at once in v0.1. Preserve model identity while merging proven duplicate file records. Hash changes invalidate compatibility/metadata caches; history retains the old identity snapshot for reproducibility.

### 6.3 Artifact and DB consistency

Write outputs to a temporary path within the target filesystem, validate media/size, flush, and atomically rename. Then commit artifact and generation records in one short transaction. If the DB commit fails, keep an orphan manifest for reconciliation rather than deleting potentially valuable output. If disk write fails, do not mark the generation saved.

On startup, reconcile unfinished output manifests, missing artifact paths, interrupted jobs, and stale process records. Retention can prune diagnostics/caches; removing originals requires a separate explicit action. A DB backup does not include model weights or generated files: export manifests must say which data is included.

## 7. Configuration specification

Illustrative future YAML; user-specific executable paths must be selected during setup:

```yaml
schema_version: 1
revision: 1
server:
  host: 127.0.0.1
  preferred_port: 6969
  port_fallback_count: 10
  remote_access: false
privacy:
  telemetry: false
  cloud_enabled: false
  nonlocal_network_allowed: false
storage:
  model_directory: ~/OXIMORON/models
  generation_directory: ~/OXIMORON/generations
  scan_roots: []
engines:
  llamacpp:
    enabled: false
    executable: null
    preferred_port: 8080
    startup_timeout_seconds: 180
  forge:
    enabled: false
    directory: null
    python_executable: null
    preferred_port: 7860
    startup_timeout_seconds: 300
  fooocus:
    enabled: false
    directory: null
    python_executable: null
    preferred_port: 7865
    startup_timeout_seconds: 300
resources:
  automatic_management: false
  idle_unload_minutes: 10
  max_gpu_jobs: 1
  vram_reserve_mib: 768
  ram_reserve_mib: 2048
desktop:
  start_with_system: false
  start_minimized: false
  restore_ui_session: true
  start_local_llm: false
  close_action: ask
logs:
  level: info
  include_prompt_content: false
  max_file_mib: 10
  backups_per_source: 5
  global_cap_mib: 250
```

Future settings may be reserved in the schema but must be marked inactive until implemented. Initial resource reserve values are conservative proposal defaults; validate against real machines. The app must not claim they guarantee OOM prevention.

Operational configuration precedence: built-in defaults → validated YAML → explicitly documented development overrides. Production per-launch CLI overrides are allowlisted and visible. UI changes update YAML atomically through the backend. Settings use revision checks so stale clients cannot overwrite newer configuration.

No arbitrary string-to-shell `command` field. Expert engine arguments are structured, validated against the selected adapter, and cannot override loopback/auth/share restrictions. Path edits take effect for subsequent jobs; active processes retain their immutable launch snapshot.

## 8. Critical algorithms and failure behavior

### 8.1 Backend bootstrap and single instance

1. Resolve user-data/runtime directories and validate ownership/permissions.
2. Acquire the data-directory supervisor lock. Do not rely on a PID file alone.
3. If locked, authenticate/identify the existing backend and attach; otherwise report stale/inaccessible state without stealing ownership.
4. Load validated config, create/migrate DB with backup, initialize services without launching engines.
5. Bind a loopback socket, first preferred port then a bounded fallback; keep the successful socket bound while initializing the HTTP server.
6. Write discovery metadata atomically and expose readiness only after required services initialize.
7. Reconcile previous jobs/process identities; no automatic inference replay.
8. On shutdown, stop admission, resolve jobs/process policy, flush records/logs, remove own discovery record, release lock.

Engine ports cannot always be reserved by passing a prebound socket. For those engines, hold a logical reservation, start promptly, detect actual bind conflicts from exit/probes, and retry only on a verified conflict. Never assume a free-port probe eliminates races.

### 8.2 Spawn, readiness, and shutdown

1. Lock engine instance; reject/return existing concurrent lifecycle operation.
2. Validate executable/cwd/model existence, policy, port, launch arguments, and available resources.
3. Record a preparing process/job record before spawn; create a separate process group.
4. Spawn with argument array and minimized environment; capture actual PID/create time/executable identity.
5. Stream stdout/stderr through bounded line parsing, redaction, rotation, and independent logging readers.
6. Poll readiness with backoff (initial proposal 250 ms to 2 seconds), checking process exit and startup deadline.
7. Mark ready only after the expected adapter probe and selected model match. Emit useful progress without inventing percentage.
8. On timeout/cancel/failure, gracefully stop only this owned process tree; after grace, revalidate identity before escalation.
9. Proposed graceful stop deadline: 15 seconds, configurable per adapter. Forced termination applies only to verified owned descendants/group membership.
10. Persist exit reason/code and release launch/resource locks even if cleanup fails. A surviving uncertain process is displayed as requiring review, not repeatedly killed.

On Linux, process group membership plus birth/executable identity is tracked; on Windows, implement job-object/process-tree ownership in its milestone. Test grandchildren and parent wrappers; killing only a shell launcher can orphan the actual server.

### 8.3 Scan and identity

1. Enumerate only registered roots, with cancellation, depth/entry budgets, and permission-error handling.
2. Use filesystem metadata before opening files. Skip sockets/devices and boundedly handle symlinks without recursion cycles.
3. Identify known extensions; parse bounded headers for supported safe formats.
4. Check file stability before/after parsing; a changing file is pending, not valid.
5. Upsert canonical location/file identity; aliases pointing to one inode/file ID do not create independent weights.
6. Compute full hashes lazily with a bounded worker and cancel support; do not hash every multi-GB file on each launch.
7. Mark missing paths only after a completed scan of the corresponding reachable root. An offline disk is “root unavailable,” not proof all models were deleted.
8. Group known shard bundles and required projector/VAE assets; report incomplete groups.
9. Mark metadata/capabilities with provenance: header, adapter probe, user override, filename inference, or verified run.

### 8.4 Deterministic routing, v0.2

1. Enforce locality/workspace restrictions before ranking.
2. Honor an explicit structured action or UI-selected capability.
3. Honor an explicit engine/model/provider only if policy/capability permits; never silently replace it.
4. Match anchored command forms and narrow natural-language patterns with attachment context.
5. Treat quoted text, negation, and requests to explain generation/code as conversational unless explicitly actionable.
6. Resolve compatible registered candidates using workspace role preferences, profile, readiness, and resource estimate.
7. If no candidate fits, explain what is missing. If ambiguity affects a side effect or cloud transfer, request selection.
8. Emit a previewable route with reason/evidence; route decisions are recorded with jobs.

Required examples: “Explain PCA” → chat; “Help me code” → configured coding preference or chat fallback with explanation; “Generate a cinematic portrait” → image; “Explain how to generate an image” → chat; “Do not generate an image” → chat; “Use ChatGPT” under Private → policy error; a sentence containing `rm -rf` → inert text, not a command; unknown image engine → selection/error.

### 8.5 Resource admission and restoration

For each resource, estimate demand as an interval. Use the conservative end for admission:

```text
admissible = observed_free - safety_reserve - pending_unreflected_reservations
allow only when estimated_new_peak <= admissible
```

Observed free memory already excludes actual resident allocations. Track reservation state so the same running allocation is not subtracted again. Pending launch/inference headroom still needs a reservation until observations catch up. Lock admission, recompute from a fresh snapshot, and grant the lease atomically.

Model estimates account for quantized weights, runtime overhead, KV cache at configured context/batch, GPU offload fraction, image dimensions/batch/pipeline, and auxiliary components. Unknown demand means conservative scheduling or explicit user confirmation; no invented precision.

v0.1: one managed GPU-heavy job at a time; block known conflicting resident engines and instruct manual stop. v0.2: plan eligible idle-owned evictions, obtain approval unless preauthorized policy covers them, recheck liveness/leases, unload, verify memory release, then dispatch.

Record previous environment before deliberate eviction. Restoration is a new admission attempt, not a rollback guarantee. If restoration fails, preserve the snapshot and explain the error; do not repeatedly oscillate between engines. Queue fairness begins FIFO with visible position and cancellability; priorities may be added only with starvation bounds.

### 8.6 Chat execution

Validate model/history/settings → append the user message once → create pending assistant record/job → reserve/prepare → stream normalized deltas → batch-persist partial content → finalize tokens/status/provenance → release lease. On error retain partial output and a safe error marker. “Retry” creates a new assistant attempt, without duplicating the user message.

Context policy: system instructions are retained; oldest complete turns may be excluded only with an explicit truncation indicator and configured policy. Do not silently summarize with an unavailable/cloud model. Validate requested output budget against configured context; exact token counts come from a tokenizer/engine where available, otherwise label estimates.

Sanitize Markdown/links; code blocks never execute. Image attachment requests check MIME/content/size and model vision capability. A projector or auxiliary model is a declared dependency, not an automatic hidden download.

### 8.7 Forge execution

Probe enabled API → list actual checkpoints/options → resolve selected registry file to engine identity → lock engine configuration → apply supported checkpoint/settings → submit txt2img → poll verified progress endpoint while request runs → handle cancel through verified interrupt scope → decode/validate/save outputs → persist effective metadata → release locks/lease.

Forge checkpoint/option changes may be global. Serialize them and detect externally modified state. If an external browser/UI session may be active, require explicit exclusive control or refuse disruptive actions. An interrupt endpoint may be engine-wide; never invoke it automatically for an unrelated attached external workload.

Timeouts are separate: HTTP connect, model startup/load, response inactivity, and total job deadline. A long image generation is not a network connection timeout. If submission outcome is unknown, query available engine history/progress before offering a retry; do not generate duplicates automatically.

### 8.8 Downloads and sharing, v0.3

Resolve a source revision and file list → validate license/gating/account requirements → check disk/reserved queue space → reuse proven existing content if present → write `.part` on destination filesystem → persist resume validators → verify size/hash → atomic rename → register → emit completion.

Resume uses Range with matching ETag/Last-Modified or equivalent immutable source revision. If a server responds with a full body or changed identity, never append it to an old partial file. Without a trusted upstream checksum, record a local content hash and label upstream integrity unverified; HTTPS and a self-computed hash are not an independent authenticity proof.

Cancel stops transfer; partial retention/deletion is explicit, with a resumable retention option. Validate URLs/redirects, disallow arbitrary local file/protocol sources, protect configured authorization headers across redirects, sanitize filenames, and prevent archive traversal/decompression bombs if extraction is later supported.

Symlink workflow: preview target/source/current state → confirm policy → verify unchanged target → back up relevant engine config if needed → create a temporary link → atomic install where supported → record manifest → verify engine discovery. Never replace a real file automatically. Windows permission failures yield a clear error/alternative; no silent copy fallback. Rollback removes only unchanged links created by OXIMORON and restores verified backups.

### 8.9 Tool execution, v0.4

Normalize model tool arguments → schema validation → canonicalize workspace paths → produce a human-readable operation plan → classify risk → obtain bound permission → revalidate exact args/path targets/policy → execute in scoped worker → cap output/time/resources → record outcome → return tool result as untrusted data to the model.

Approval hashes bind principal, workspace, tool, exact arguments, canonical paths, policy revision, and expiry. A changed operation invalidates the approval. UI approvals and tool outputs use separate channels; text saying “approved” cannot grant authority.

Filesystem traversal/symlink races require handle-based or equivalent safe operations, not only a preflight `realpath` check. Terminal execution uses argument arrays and narrow command-specific validators; pipes/redirects/substitution require an explicit shell execution approval. Git hooks and external diff/pager execution must be disabled or treated as untrusted execution. Python and arbitrary browser actions remain powerful tools with explicit scope.

## 9. Frontend implementation contract

- Organize by feature, with shared primitives for status badges, metric values, engine selector, model picker, job progress, error/action panel, approval dialog, and virtualized log viewer.
- Generated types and one transport layer handle auth, request IDs, idempotency, cancellation, and reconnect. No feature creates a private unauthenticated fetch path.
- Server-state cache invalidation follows entity/job events. Optimistic updates are limited to reversible metadata such as favorite state, not process readiness.
- Use query cancellation/debouncing for model search and scanner results. UI unmount does not accidentally cancel a durable image job.
- Resource decisions and routing reasons are visible in job detail. Backend disconnection replaces live numbers with stale timestamps.
- Model compatibility badges distinguish inferred, verified, unsupported, and unknown.
- Native file pickers return selected locations; backend validates scope. Browser development mode must not pretend to have Tauri privileges.
- Never render sample engines/GPU metrics as real in production. Fixtures belong to explicit development/test mode.
- Local fonts/assets; no CDN dependency for startup. No telemetry, analytics SDK, remote image dependency, or cloud auth gate.
- Secrets fields are write-only: entered key is submitted to backend keyring storage, then cleared. Subsequent UI displays only configured/not configured.
- Long operations expose cancel, latest stage, and actionable errors; progress percentages only when supported.

## 10. Delivery work packages

Each package below is initially `not_started`. Dependencies reference other packages. Files are intended ownership areas, not instructions to create every file upfront.

### M00 — Feasibility, version matrix, and repository baseline

Release: v0.1. Dependencies: none. Estimate: 2–4 focused days.

Deliver: selected/pinned Python, Node/pnpm, Rust/Tauri versions; minimal package import layout; development tasks; compatibility checklist; ADRs for sidecar/API/storage; packaging feasibility result; definitions of mocked versus real engine tests. Inspect actual installed-engine versions only when implementation is authorized and paths are in scope.

Investigate: Tauri webview prerequisites on target Ubuntu; packaged Python startup/RSS; keyring availability/locked behavior; NVML availability; llama.cpp executable flags and health; Forge launch/API authentication; Fooocus safe launch method. Do not run unknown scripts during discovery.

Acceptance: a documented version matrix with evidence or explicit gaps; backend dependency set excludes torch/transformers/inference runtimes; no ambiguous shared Python environment; packaging approach demonstrated with a minimal no-inference executable. Choose supported adapter builds before claiming compatibility.

### M01 — Desktop shell and bootstrap boundary

Release: v0.1. Depends: M00. Estimate: 3–5 days.

Deliver: `apps/desktop` React/Tauri shell, local assets, dark design tokens, navigation for implemented destinations, accessible components, native backend bootstrap interface, disconnected/empty states, window settings. Build the geometric brand mark as a simple local asset during implementation.

Acceptance: desktop launches offline; keyboard navigation/focus work; window resizing does not break layout; unavailable pages are not fake functional UI; packaged native bridge cannot execute arbitrary frontend-provided programs. Mock data is visibly restricted to development.

### M02 — Backend, persistence, configuration, and authenticated transport

Release: v0.1. Depends: M00, M01 bootstrap contract. Estimate: 4–6 days.

Deliver: FastAPI app factory/lifespan; single-supervisor lock; protected bootstrap/discovery; schema and migrations for P0 entities; validated atomic YAML settings; typed errors; REST auth; exact-origin policy; ticketed WebSocket; generated API types; short-transaction repositories; backup/recovery handling.

Acceptance: second instance attaches or fails safely; occupied 6969 selects a recorded safe fallback; unauthenticated/cross-origin requests fail; bad YAML preserves prior config; migration failure preserves DB backup; credentials never appear in URLs/logs; clean shutdown removes only its own runtime record.

### M03 — Adapter protocol, service composition, and explicit orchestration

Release: v0.1. Depends: M02. Estimate: 2–4 days.

Deliver: adapter protocols/DTOs, builtin registry, capability matrix, explicit task dispatcher, job/event lifecycle, idempotency storage, cancellation primitive, bounded event queues, deterministic fake adapter for contract tests. No natural-language router yet.

Acceptance: unsupported capabilities return typed errors; duplicate submission produces one job; cancellation/failure releases resources; event replay/snapshot reconciliation handles reconnect; a slow event consumer cannot exhaust memory; transport does not import concrete adapter internals.

### M04 — Discovery, owned process supervision, and port management

Release: v0.1. Depends: M03. Estimate: 5–7 days.

Deliver: shallow candidate discovery/manual registration; validated launch specs; subprocess groups; ownership DB records; ready probes; bounded logs; serialized lifecycle; logical port reservations/retry; startup timeout; stale PID reconciliation; sanitized environments.

Acceptance: fake engines test readiness delay/failure, port race, stdout flood, child/grandchild cleanup, simultaneous start, stop-during-start, crash exit, PID identity mismatch, and unrelated process safety. Discovery has no execution side effects. Logs remain bounded/redacted. No healthy state from an unrelated open port.

### M05 — llama.cpp adapter and first real local response

Release: v0.1. Depends: M04. Estimate: 3–5 days.

Deliver: registered executable validation; explicit GGUF path selection pending registry UI; loopback launch with supported flags; `/health` probe; selected-model identity; normalized OpenAI-compatible chat streaming; cancellation; CPU fallback option; stop-based unload when needed. Disable bypass tool execution.

Acceptance: real selected small GGUF produces a streamed answer offline; invalid model fails clearly; wrong executable/API is rejected; no unsupported load/unload route is assumed; cancellation/stop clean up the owned server; CPU-only operation or hardware gap is recorded honestly. Record exact engine build/model/hardware.

### M06 — Model scanner and central registry

Release: v0.1. Depends: M02, M03; integrates with M05. Estimate: 3–5 days.

Deliver: roots/settings; incremental/cancellable scan; GGUF/safetensors bounded parsing; other formats inventoried as unknown; canonical identities; lazy hash jobs; shard/auxiliary dependency representation; model detail/filter/favorite endpoints; adapter compatibility metadata.

Acceptance: nested files, spaces/unicode, inaccessible roots, symlink cycles, aliases/hardlinks, changed/missing files, malformed/oversized headers, partial downloads, incomplete bundles, and duplicate names behave correctly. Scan neither executes model code nor copies weights. A selected registered GGUF launches through M05.

### M07 — Forge and Fooocus lifecycle adapters

Release: v0.1. Depends: M04, M06. Estimate: 3–5 days.

Deliver: separately configured engine directories/interpreters; version-aware launch validation; Forge API-enabled readiness and checkpoint mapping; Fooocus start/stop/open; capability/unsupported states; no auto-install/download/update launch wrappers.

Acceptance: real Forge starts and exposes required verified API routes; incompatible API configuration has actionable diagnostics; Fooocus lifecycle works for the supported installed build or is explicitly unqualified. Starting either does not mutate existing environments. No integrated Fooocus generation claim without evidence.

### M08 — Hardware telemetry and conservative admission

Release: v0.1. Depends: M04; integrates M05/M07. Estimate: 2–4 days.

Deliver: psutil snapshot service; optional NVML provider; disk availability; per-process CPU/RAM/GPU fields where supported; stale/unsupported markers; adaptive sampling; one managed GPU-heavy job queue; known conflict rejection and resource diagnostics.

Acceptance: no-NVIDIA, NVML permission/error, disappearing process, stale data, and disk-full paths work; UI thread stays responsive; CPU jobs are not mislabeled GPU workloads; conflicting launches cannot race past admission; no automatic eviction occurs in v0.1.

### M09 — Chat UI and durable conversation path

Release: v0.1. Depends: M01, M05, M06, M08. Estimate: 3–5 days.

Deliver: model selector; messages; sanitized Markdown/code; streamed response; cancel/retry; system prompt/temperature/context; partial and completed persistence; conversation reopen; empty/disconnected/error states; CLI-ready chat API.

Acceptance: local real answer from UI; partial stream preserved after failure; reconnect does not duplicate content; cancel affects the right job; context overflow is explained; hostile HTML/code remains inert; reload restores saved conversation. Vision/attachments remain unavailable until supported.

### M10 — Forge Image Studio and artifact persistence

Release: v0.1. Depends: M07, M08, M06, M01. Estimate: 3–5 days.

Deliver: prompt/settings/checkpoint UI; job/progress/cancel path; engine-global configuration lock; image saving + effective metadata; detail/reuse settings; artifact serving; disk/output validation and orphan reconciliation.

Acceptance: real Forge image is visible and stored with model/settings/seed/provenance; app reload reopens it; cancel/timeout/disk failure are distinguishable; external engine activity is not interrupted; unsupported settings are rejected, not silently ignored. Prompt “cat driving a WagonR” can be used as a manual smoke request, with quality judged separately from plumbing.

### M11 — Operational UI, CLI, palette, and integration hardening

Release: v0.1. Depends: M09, M10. Estimate: 3–5 days.

Deliver: Home/Engines/Models/System/Logs/Settings connected to real services; setup flow; model/engine search; basic Ctrl+K navigation and engine actions; Typer CLI with status/run/ask/generate/logs and JSON mode; error/cancel semantics; API integration documentation.

Acceptance: CLI and UI control the same jobs/state; no second engine launched by a concurrent CLI start; noninteractive permission needs return a clear exit code; secrets redacted across surfaces; required screen states and keyboard access covered. All local flows work with network disabled.

### M12 — v0.1 packaging, fault testing, and release gate

Release: v0.1. Depends: M11. Estimate: 4–6 days.

Deliver: versioned backend sidecar packaged into Tauri; Linux package/run instructions; engine compatibility matrix; benchmark report; release checklist; crash/shutdown/uninstall data-preservation behavior; selected license/distribution notices before publication.

Acceptance: all criteria in `plan.md` section 5; cold/warm launch and idle budgets measured; backend kill, engine kill, UI close, laptop sleep/resume, occupied ports, low disk, missing models, unavailable GPU, and offline startup tested. A clean supported Linux machine can launch without a developer virtualenv. Uninstall preserves user data/weights by default. GPU/desktop tests cannot be replaced by a successful HTTP route test.

Exit: qualified v0.1 or an explicitly labeled preview with named failed/unverified gates. Re-estimate later phases based on measured effort.

### M13 — Deterministic routing, modes, and expanded history

Release: v0.2. Depends: M12.

Deliver: routing preview/reasons; intent rules/evaluation corpus; Auto/Local/Cloud/Image UI semantics; task-role preferences; rich conversation history and recent generations; local searchable content; attachment/vision capability plumbing where verified.

Acceptance: routing cases in section 8.4 plus realistic ambiguous/negated/multilingual inputs; no Local→cloud fallback; unavailable capabilities produce a selection/error; explicit engine overrides respected; malicious text cannot trigger tool execution. Cloud mode remains unavailable until M15 provider configuration succeeds.

### M14 — Automatic resources, recovery, and environment restoration

Release: v0.2. Depends: M13, M08.

Deliver: demand estimates with confidence; durable lease ledger; idle tracking/unload; approved/preauthorized eviction; model switching; improved orphan reconnect/explicit attach UI; resource approval primitive; restore snapshots; hardware recommendations using measured peaks.

Acceptance: simultaneous admissions do not over-reserve; resident usage is not double-counted; active jobs/external engines never auto-evicted; approvals expire/revalidate; model switch with OOM leaves clear recoverable state; Qwen→Forge→restore works on reference hardware or the compatibility gap is recorded. Backend restart never replays a paid/side-effectful request.

### M15 — Cloud provider adapters and provider safety

Release: v0.2. Depends: M13, M02 security contract.

Deliver: provider protocol + adapters for OpenAI-compatible/OpenAI, Gemini, Anthropic, OpenRouter; OS keyring references; explicit provider settings/test; stream normalization; option/capability validation; rate limits/cooldowns; privacy disclosures; configurable request budgets.

Acceptance: each claimed provider has contract fixtures and a separately authorized live smoke call; missing/locked keyring has no plaintext fallback; private/local/offline policies block external requests before dispatch; no credential forwarding across redirects; 429/retry/partial stream behavior safe; no retry after ambiguous chargeable outcome. Live calls require available credentials and deliberate cost acceptance; no test should use paid calls unexpectedly.

### M16 — Workspaces, profiles, tray, search, and v0.2 gate

Release: v0.2. Depends: M14, M15.

Deliver: Photography/Development/Private workspace templates; Fast/Quality/Private/Battery/Maximum profiles; immutable job policy snapshots; scoped global search; tray/autostart/minimized/session options; compatibility facade including embeddings only when verified; full v0.2 docs.

Acceptance: profile/workspace precedence tests; switching UI workspace does not mutate active jobs; private policy blocks all non-loopback OXIMORON traffic; tray unavailable fallback works; autostart is opt-in; UI session restore does not replay work; compatibility API and CLI obey identical policies. v0.2 gate includes offline regression and hardware restoration tests.

### M17 — Downloads, shared model storage, and new engine integrations

Release: v0.3. Depends: M16.

Deliver: Hugging Face model-source adapter with immutable revisions/gating; resumable queue; disk reservations; verification; shared-path/symlink plan/apply/rollback; LoRA/VAE/ControlNet registry roles; ComfyUI/Ollama adapters; Fooocus generation bridge feasibility and optional integration.

Also deliver explicit installation recipes for supported engines: selected source/version, license, required disk/network, isolated destination/environment, checksums where provided, preflight dependencies, progress/cancel, and failure cleanup limited to newly created owned files. Existing installations are registered rather than overwritten. Missing system dependencies produce manual instructions; no automatic sudo, driver changes, or launch-time updates. Automatic engine upgrades remain outside this milestone.

Acceptance: pause/resume across restart; changed ETag/full-body-on-resume; checksum mismatch; disk full; interrupted atomic commit; no duplicate downloaded bytes when a proven existing file can be reused; symlink collision/rollback; explicit Ollama storage limitations; ComfyUI workflow/model/node dependency validation. Fooocus bridge is either supported with pinned evidence or remains visibly unsupported; it is not replaced silently with a third-party service.

Installation acceptance: cancel/failure preserves pre-existing files and environments; installation never starts an engine or downloads weights without those steps being included in the approved plan; unsupported platform/dependency requirements fail before mutation. Record every installed component/source version for support and removal.

### M18 — Advanced studio, gallery, and v0.3 gate

Release: v0.3. Depends: M17.

Deliver: virtualized searchable gallery; metadata details; prompt/settings reuse; variants; img2img/inpaint/outpaint/upscale/background removal/face restoration through compatible installed capabilities; ControlNet/LoRA controls; validated ComfyUI templates and progress; explicit overrides for engine selection.

Acceptance: each advertised operation has a real compatible-engine smoke result; masks/dimensions/input MIME validated; provenance preserved; no unsupported operation displayed as ready; original artifacts are never overwritten by default; shared weights remain shared; full offline regression. Missing capabilities may stay unavailable but cannot be counted complete without a documented scope decision.

### M19 — Permission system and local tools

Release: v0.4. Depends: M18 and permission foundations M14.

Deliver: tool schema registry; plan/execute separation; bound approvals; grant management/revocation; scoped filesystem/terminal/Git/Python tools; explicit browser integration; time/resource/output limits; per-call audit records; no native model bypass tool execution.

Acceptance: traversal/symlink race cases; changed arguments after approval; expiry/revocation; workspace mismatch; shell injection; unsafe Git hooks/config; secret/log leakage; cancellation; child-process cleanup; output flood; prompt injection cannot self-authorize. Define platform isolation honestly; disabling a button is not enforcement.

### M20 — MCP, controlled workflows, and v0.4 gate

Release: v0.4. Depends: M19.

Deliver: versioned MCP connector transport, health/reconnect/timeouts; local/remote registration; tool schema validation; tool-call normalization; agent loop with max steps, time/cost/output limits, stop control, and per-step audit UI.

Acceptance: a compatible model executes an approved read-only file task; write/delete is blocked pending bound approval; remote MCP is blocked in Private mode; server disconnect/schema change/oversized output handled; repeated tool loop ends at configured budget; approval text from model/tool output has no authority. User can interrupt the entire workflow and inspect what actually ran.

### M21 — Plugin SDK and portability/export foundations

Release: v1.0. Depends: M20.

Deliver: versioned manifests/host protocol; engine/provider/tool/model-source SDK examples; isolated execution and permission grants; UI plugin isolation design; provenance/integrity/compatibility checks; marketplace index/install architecture; versioned workspace/config exports with secret/path portability rules.

Acceptance: sample plugin cannot gain undeclared host permissions; incompatible manifest fails safely; disable/uninstall leaves user models/data intact; malformed plugin output contained; imports preview conflicts and do not execute included scripts; secret references exported without secret values; external machine paths require remapping. Public marketplace operation remains a separate product commitment.

### M22 — Remote mode, multi-GPU, Windows, updates, and v1.0 gate

Release: v1.0. Depends: M21.

Deliver: opt-in authenticated TLS remote API with scoped access/rate limits; web/phone-responsive client; device-aware reservations/scheduling; tested Linux+Windows packages; signed update/rollback path; stable API/SDK compatibility policy; full operational runbooks.

Acceptance: remote threat review and auth/session tests; default remains loopback; GPU affinity respected across competing jobs; supported Windows process/keyring/link/tray paths validated on Windows; signature/version/rollback checks pass; update preserves config/DB/artifacts with migration backup; supported platform clean installs and offline flows pass. Do not label v1.0 if these committed deliverables remain only mocks.

## 11. Dependency overview

```text
M00 -> M01 -> M02 -> M03 -> M04 -> M05
                            |       |
                            +--> M06 +--> M07
                                      \    /
                                        M08
                                      /     \
                                    M09     M10
                                      \     /
                                        M11 -> M12 (v0.1)
                                                 |
                                                M13
                                               /   \
                                             M14   M15
                                               \   /
                                                M16 (v0.2)
                                                 |
                                             M17 -> M18 (v0.3)
                                                 |
                                             M19 -> M20 (v0.4)
                                                 |
                                             M21 -> M22 (v1.0)
```

The diagram summarizes flow; each milestone's dependency list is authoritative. Independent work may be done concurrently by human contributors if interfaces are frozen. Automated delegation is not required by this plan and must not be inferred from this diagram.

## 12. Test strategy

### 12.1 Layers

| Layer | Proves | Does not prove |
| --- | --- | --- |
| Unit | Policy, routing, metadata parsing, state transitions, estimates | Real engine/API/hardware compatibility |
| Adapter contract | Request/response mapping and versioned fixtures | An installed engine can load a real model |
| Process integration | Spawn, ports, identity, logs, cancellation with controlled helper processes | Actual GPU memory release |
| API/database integration | Transactions, auth, idempotency, events, migrations | Desktop native lifecycle |
| Browser UI E2E | User flows, rendering, accessible controls against test backend | Tauri IPC/tray/packaging behavior |
| Real engine integration | Inference/output behavior for recorded versions/models | Other builds/models/hardware |
| Packaged desktop/hardware | Actual install, native lifecycle, GPU, offline, keyring | Untested operating systems or remote safety |

Backend tools: pytest + async support + HTTP test client + contract fixtures; property-based cases where parser/state invariants justify them. Frontend: TypeScript checks, component tests for meaningful behavior, Playwright for browser flows. Tauri-native tests/manual packaged smoke are separate. Linters/formatters and generated-schema checks run in CI.

### 12.2 Mandatory adversarial/fault matrix

- Process: PID reuse, externally owned process, bind race, orphaned child, hanging readiness, crash during startup, failed termination.
- Policy: Local→cloud blocked, Private→remote catalog blocked, remote redirect blocked, conflicting profile/workspace restrictions.
- Resources: concurrent admissions, stale telemetry, no NVML, external GPU use, memory not released after unload, OOM, restoration failure.
- Persistence: process crash before/after artifact rename, DB lock/disk full, migration failure, invalid YAML, stale revision, interrupted scan/hash.
- Streaming: disconnect/reconnect, slow consumer, duplicate/out-of-order events, expired cursor, partial provider response, cancellation race.
- Models/downloads: malicious headers, path traversal, symlink cycles, incomplete shards, changing source, duplicate content, checksum mismatch.
- Security: hostile Origin/Host, missing token, ticket replay, secret in stdout/URL, XSS Markdown, prompt injection, unsafe custom launch flags.
- Desktop: tray unavailable, backend unavailable, second launch, sleep/resume, close/exit distinction, offline clean start, scale/window resizing.

### 12.3 Planned checks and evidence

During M00, define reproducible tasks equivalent to:

```text
uv run ruff check .
uv run pytest tests/unit tests/contract tests/integration
pnpm --filter @oximoron/desktop typecheck
pnpm --filter @oximoron/desktop test
pnpm --filter @oximoron/desktop build
cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml
```

These commands are proposals and will not work until scaffolding/package scripts exist. Native E2E, live provider, real-engine, and hardware tests use explicit opt-in markers/commands; ordinary CI must not launch unknown installations, download weights, spend API credits, or require a GPU.

Evidence record fields: milestone, revision, date, test command/steps, host OS/architecture, app/engine build, model identity/hash if known, CPU/GPU/RAM, pass/fail/skipped reason, artifact/log location, and practical limitation. Do not put credentials or private prompts into public test evidence.

## 13. Observability and runbooks

Structured log fields: UTC timestamp, level, component, request/job/engine/process IDs, event code, safe message, elapsed time, and retry count. Redaction occurs before disk storage and before event/UI export. Disable raw HTTP bodies by default. Maintain an explicit allowlist of diagnostic metadata rather than logging arbitrary objects.

Log viewer supports OXIMORON/llama.cpp/Forge/Fooocus/ComfyUI filters as available, severity, bounded search/tail, pause display, and redacted export. Holding UI display must not stop the process pipe reader and deadlock an engine.

Required future runbooks: first setup; engine path/API validation; failed start; GPU unavailable/OOM; occupied port; stale process/reconnect; keyring locked; invalid config rollback; DB backup/migration recovery; download integrity failure; offline operation; supported-engine upgrade; package install/update/uninstall; data export/import; privacy and permission reset.

## 14. Release checklist template

- [ ] All milestone deliverables for this release implemented, with no fake-success placeholders.
- [ ] Automated tests and static/build checks pass for the current revision.
- [ ] Relevant real-engine/provider behavior verified, or release labeled preview with explicit gaps.
- [ ] Packaged desktop and supported-platform behavior tested.
- [ ] Offline/locality, process ownership, auth, and secret handling verified.
- [ ] Resource budgets measured and regressions explained.
- [ ] Migration/backup/recovery/uninstall preserves existing user data.
- [ ] API/types/schema and compatibility documentation updated.
- [ ] Third-party licenses/distribution obligations reviewed before shipping bundled components.
- [ ] User-facing release notes separate implemented behavior from upcoming features.

## 15. Immediate next action after implementation authorization

Begin M00 only. Produce the actual toolchain/engine compatibility inventory, packaging feasibility evidence, package boundaries, and reproducible development tasks. Then implement the Tauri shell and authenticated backend path in M01–M02. The first functional integration target is a real local llama.cpp response; the first release finish line is M12, not a static dashboard.
