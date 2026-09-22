# ADR 0002: Local API Authentication and Transport Security

## Status
Accepted (2026-09-22)

## Context
Even though OXIMORON binds strictly to `127.0.0.1` by default, running an unauthenticated HTTP API on loopback exposes the system to Cross-Site Request Forgery (CSRF) from malicious web pages running in any browser on the local machine (e.g., DNS rebinding or WebSockets). Furthermore, credentials must not leak into process command-line arguments, environment variables, browser localStorage, or ordinary logs.

## Decision
1. **Bearer Token Authentication:** All mutating and data-retrieval routes under `/api/v1` require an `Authorization: Bearer <token>` header.
2. **Token Generation & Storage:**
   - On backend startup, a cryptographically secure random token is generated.
   - The token reference is stored in the OS keyring (`gnome-keyring` via `secret-tool` or Python `keyring`).
   - If the keyring is unavailable or locked, an owner-readable (`0600`) runtime credential file (`~/.oximoron/run/credentials.json`) is used for the active session and destroyed on clean shutdown.
   - The token is never written to public logs, command-line arguments, or git.
3. **Origin & Host Validation:**
   - FastAPI middleware validates the `Host` header (must match loopback/port).
   - In production, incoming `Origin` headers from web browsers are restricted to Tauri's internal origins (`tauri://localhost` or `http://tauri.localhost`), rejecting unauthorized web browser origins. Development mode explicitly whitelists Vite development servers.
4. **WebSocket Security:**
   - Direct connection without authentication is rejected.
   - Clients request a one-time WebSocket ticket via `POST /api/v1/events/ticket` (authenticated by Bearer token).
   - The ticket has a 30-second TTL and can be used exactly once to upgrade to `WS /api/v1/events`.

## Consequences
- Robust protection against loopback port scanning, unauthorized local access, and browser-based CSRF attacks.
- CLI and desktop UI share the exact same authenticated API transport.
