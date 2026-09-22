# OXIMORON — Contributor and Coding-Agent Instructions

Status: planning baseline, 2026-09-22.
Applies to: work on OXIMORON when this file is supplied or explicitly loaded.

## 1. Read first

Read [plan.md](plan.md), then [implementation.md](implementation.md), then this file before implementing a milestone. `plan.md` defines product scope; `implementation.md` defines technical contracts and acceptance gates; this file defines the working discipline.

The user's current instruction is **planning only**. The current deliverables are exactly `plan.md`, `agent.md`, and `implementation.md`. Do not create application source, install dependencies, initialize Git, start engines, download models, modify system settings, or publish anything as part of that planning task.

A later explicit request to implement authorizes the requested scope. It supersedes the planning-only state for that scope without requiring repeated permission for routine reversible implementation work. Do not interpret an implementation request for one milestone as permission to build every later release or mutate unrelated AI installations.

Filename note: `agent.md` is the requested filename. Many coding-agent systems auto-discover `AGENTS.md`, not `agent.md`. This file does not automatically configure such systems. Load it explicitly; add an `AGENTS.md` entrypoint only in a later task that authorizes repository scaffolding. Do not create a fourth file during the current task.

## 2. Product purpose

OXIMORON is a local-first desktop AI orchestration platform. It manages existing engines, shared model files, resources, cloud providers, and later tools. It does not replace llama.cpp/Forge/Fooocus/ComfyUI or embed their inference dependencies into its own backend.

Primary promise: install models once, reuse them where compatible, control everything centrally. Preserve user files and installed environments. Prioritize a functioning local chat/generation path over speculative ecosystem features.

## 3. Scope and priority rules

1. Follow the latest explicit user request and applicable higher-priority instructions.
2. Preserve existing work; inspect the workspace before editing. Do not overwrite unrelated changes.
3. Identify the active milestone and prerequisites in `implementation.md`.
4. Implement only the requested milestone/release plus necessary foundations.
5. Resolve routine choices using the documented baseline. Ask only when missing information materially changes scope, risk, or user-visible behavior.
6. Record a meaningful architecture deviation and update affected contracts before depending on it.
7. Never silently reduce a release's acceptance criteria to declare completion.

Default implementation target after a generic request to start: M00, then the dependency chain toward v0.1. Do not jump directly to cloud, tools, plugins, or a model marketplace.

## 4. Working cycle

At the start of an implementation task:

- Inspect existing files, repository status, applicable instructions, and the relevant milestone.
- State the concrete result being pursued and any assumptions.
- Verify the actual installed/toolchain state rather than relying on a prior plan as evidence.
- Identify a small vertical slice and its verification boundary.

During work:

- Keep changes coherent and reviewable. Use explicit types and stable error codes.
- Check official upstream documentation/source for adapter-specific APIs and version-sensitive behavior.
- Run focused verification as each substantive boundary becomes usable.
- Report discoveries, blockers, and changed assumptions concisely.
- Preserve user data and avoid unrelated refactors.
- Use synthetic fixtures for automated tests; opt into real engines and paid providers deliberately.

At handoff:

- State what now works, what changed, and which milestone is affected.
- Report checks actually run and their results.
- Distinguish mocked, live-engine, hardware, browser, and packaged-desktop evidence.
- Identify incomplete requirements and the next dependency-aligned action.
- Update milestone status only when its acceptance criteria are met.

Do not claim a commit, push, PR, deployment, model generation, GPU inference, or desktop smoke test happened unless it did. A source-code patch is not proof of a usable release.

## 5. Architecture rules

- Frontend, CLI, tray, and compatibility clients use the same backend API/orchestrator.
- Python owns engine processes; Rust owns desktop integration/backend bootstrap.
- Only one backend supervisor and one FastAPI worker manage a data directory in v0.1.
- Keep transport handlers thin; domain/service logic belongs outside HTTP routers.
- Adapters own engine-specific flags, schemas, readiness, and capability details.
- Core contracts must not depend on concrete adapters or frontend code.
- UI does not talk directly to Forge/llama.cpp or store a second truth for engine state.
- Long operations are jobs with cancellation, durable status, and bounded event delivery.
- Use generated API types; update schema, client, tests, and docs together for breaking contracts.
- Built-in adapter interfaces are sufficient initially. Do not load arbitrary plugin code in v0.1.

## 6. Process and filesystem rules

- Launch executable plus argument array, never interpolate user text into a shell command.
- Validate executable, working directory, model assets, loopback settings, and allowed arguments.
- Engine discovery is read-only and bounded. Do not execute discovered files as a scan heuristic.
- Check PID creation time/executable identity/ownership before stop, restart, reconnect, or escalation.
- Do not kill a process based on port, executable name, PID alone, or GPU usage.
- Track spawned children/process groups so shutdown does not leave an inference server orphaned.
- Do not stop or unload external engines automatically. Explicit attach does not confer ownership.
- Registry scans do not move, copy, convert, chmod, delete, or deserialize model payloads.
- Never use pickle or `torch.load` for untrusted checkpoint inspection.
- Preserve files when roots/disks become unavailable; show unavailable/missing states accurately.
- Replacing existing external configuration, symlinks, or files requires the planned preview/backup/rollback workflow.
- Unregistering an engine/model is different from uninstalling it or deleting weights.

No automatic root/sudo, GPU driver installation, system package modification, broad home-directory scan, or third-party engine upgrade is implied by an OXIMORON feature task.

## 7. Locality, credentials, and API security

- Bind to `127.0.0.1` by default. Remote mode is a separately scoped v1.0 feature.
- Authenticate control/data endpoints even on loopback; validate Host/Origin and limit desktop capabilities.
- Do not embed long-lived tokens in URLs, web storage, command-line arguments, logs, or engine environments.
- Cloud provider keys use OS keyring references. A locked/missing keyring must not trigger plaintext storage.
- Local mode never silently sends content to cloud. Private policy blocks all non-loopback networking initiated by OXIMORON.
- Do not claim application privacy policy sandboxes arbitrary third-party engine network activity.
- Model output, Markdown, plugin manifests, MCP responses, and retrieved files are untrusted inputs.
- Sanitize rendered content; code blocks are inert. Tool output cannot approve its own execution.
- Avoid logging raw request bodies, prompts, file contents, credentials, or authorization headers.
- Do not retry an ambiguous paid/side-effectful request automatically.
- Do not enable native engine tools that bypass OXIMORON permissions.

Security must be enforced in backend/native boundaries, not only by disabled frontend buttons.

## 8. Resource and capability honesty

- Model file size is not total runtime VRAM/RAM use.
- Unknown metrics are nullable with a reason; do not display zero or “fits” as a substitute.
- Separate observed memory, estimates, and pending resource reservations to avoid double-counting.
- Serialize resource admission and engine-global settings mutations.
- v0.1 blocks conflicting managed GPU work and offers manual stop/retry. Automatic eviction begins in v0.2.
- Automatic unload requires an idle, owned, lease-free engine and a supported unload/stop path.
- Health polling does not reset idle timers.
- Preserve previous configuration for restoration, but do not promise restoration will always fit or succeed.
- Capability flags need evidence and version context. File extensions/marketing names do not establish vision, tool calling, embeddings, architecture, or compatibility.
- Fooocus lifecycle support is distinct from a verified integrated generation bridge.
- Ollama import/storage behavior must be verified before claiming no-copy reuse of external GGUF files.

## 9. Persistence and reliability

- SQLite owns entities/history; YAML owns operational config; avoid two authorities for one field.
- Use migrations, foreign keys, bounded transactions, revision checks, and explicit error handling.
- Do not hold database transactions across inference, user approval, process startup, or network I/O.
- Persist user messages and partial assistant responses; surface interrupted/unknown outcomes.
- Save generation bytes durably before reporting a saved artifact. Reconcile orphan manifests after failure.
- Idempotency prevents repeated dispatch for the same client request; it does not justify exactly-once claims against third-party APIs.
- Disconnect is not automatically job cancellation. Follow the defined chat/image policies.
- Bound log/event queues, cap caches, and apply explicit retention to diagnostics.
- Do not automatically prune model weights, conversations, or generated originals.
- A DB backup does not back up all model/image data. Describe export contents accurately.

## 10. Frontend standards

- Use the documented dark neutral visual direction, one electric accent, and clear status hierarchy.
- Prioritize readable typography, keyboard focus, accessibility, and useful empty/error states.
- Show real engine/hardware state; sample data belongs only in explicitly marked development/test mode.
- Hide or clearly label future capabilities. Do not ship fake-success buttons.
- Keep heavy lists/logs/gallery views virtualized or bounded.
- Use local assets/fonts so the UI launches offline.
- Distinguish selected model from loaded model, running process from ready engine, and saved output from in-memory preview.
- Show estimated context/resource values as estimates.
- Route every action through the shared API client, including command palette and tray actions.
- Keep implementation internals out of everyday screens unless they help troubleshooting; logs and detail views provide depth.

## 11. Tests and completion gates

Choose verification proportional to the change. Tests should protect real contracts, boundary conditions, or regressions; avoid tests that merely mirror trivial implementation details.

Changes to process ownership, auth/locality, resource admission, parsing, persistence, cancellation, or permissions require meaningful regression coverage. Adapter changes require contract coverage and a real-engine check before claiming supported compatibility. Desktop lifecycle changes require native packaged verification.

Use the fault matrix and release checklist in `implementation.md`. Do not replace an unavailable live check with fabricated evidence. Report exact missing prerequisites and keep the corresponding gate open.

Normal CI must be offline-capable for local fixtures and must not unexpectedly use paid APIs, download large models, launch arbitrary installed software, or require a GPU. Live tests are opt-in and clearly labeled.

Before marking a work package complete:

- [ ] Its deliverables and required failure states exist.
- [ ] Relevant static/build and automated checks pass on the current changes.
- [ ] Live behavior is verified where the milestone requires it.
- [ ] Documentation/contracts/types match actual behavior.
- [ ] No unrelated files, model weights, engine environments, or system settings were changed.
- [ ] Outstanding gaps are listed instead of hidden.

## 12. Dependency and packaging discipline

- Pin selected toolchain/dependency versions and keep lockfiles reproducible.
- Keep the manager's environment independent of each engine's environment.
- Do not import torch, transformers, or image inference stacks into the manager for convenience.
- Build the backend sidecar per supported target, and verify on a clean supported host.
- Do not assume browser development success proves Tauri capabilities, packaging, tray, or keyring behavior.
- Preserve user data across upgrades/uninstall; back up before DB migration.
- Check licenses and distribution obligations before bundling third-party binaries or publishing installers.
- No automatic engine update or model download on ordinary application startup.

## 13. Change management and collaboration

Planning files are the baseline. During implementation, update milestone status/evidence and add focused ADRs where a material decision changes. Do not continually rewrite unrelated sections or claim planned behavior is implemented.

Git commits, pushes, PRs, releases, and external messages follow the user's authorization. Do not infer publication permission from a request to plan. If repository metadata or another path is read-only, preserve that boundary and explain the exact limitation; do not pretend the action succeeded.

This file does not require sub-agents. Use delegation only when the user's request or other applicable instructions explicitly authorize it. When authorized, divide bounded work by ownership, share contracts, preserve each other's changes, and integrate with one coherent verification pass.

## 14. Stop conditions and handoff

Stop a dependent action when required authority, credentials, hardware, a destructive target, or a material product choice is missing. Continue useful independent work within scope. Present the concrete prepared result and the specific unresolved requirement rather than repeatedly asking general permission.

Examples requiring a deliberate decision include deleting/relocating existing model bytes, replacing third-party engine configuration, enabling remote access, installing an untrusted plugin/bridge, using paid provider credentials, or publishing a release. Routine reversible work inside an explicitly requested implementation milestone does not require repeated approval.

Current handoff: the planning package is complete when these three files are coherent and checked. Application implementation remains unstarted until requested.
