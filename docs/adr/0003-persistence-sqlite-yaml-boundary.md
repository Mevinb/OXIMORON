# ADR 0003: Persistence Architecture — SQLite and YAML Separation

## Status
Accepted (2026-09-22)

## Context
OXIMORON persists both human-editable configuration (server ports, privacy settings, engine directories) and high-volume relational records (conversations, streamed messages, image generation history, model catalog, process inventories, jobs, and audit events).

Storing everything in a relational database makes manual troubleshooting and portable configuration difficult. Storing everything in YAML files leads to corruption, concurrency issues, lack of query indexing, and difficult migrations.

## Decision
1. **YAML (`config.yaml`):**
   - Authoritative for operational and environment configuration (ports, directories, privacy flags, log levels, default engines).
   - Validated strictly via Pydantic models on load.
   - Written atomically using a temporary file and atomic rename (`os.replace`) to prevent file corruption.
   - Includes schema versioning and optimistic revision checks.
2. **SQLite (`oximoron.db`):**
   - Authoritative for entities, relational data, and time-series records (models, files, engine process records, jobs, conversations, messages, generations, artifacts).
   - Uses SQLAlchemy 2.0 async engine and Alembic for versioned schema migrations.
   - Operates in WAL mode (`PRAGMA journal_mode=WAL`) with foreign keys enabled (`PRAGMA foreign_keys=ON`).
   - Short, bounded transactions. Transactions are never held open across long-running operations (inference, subprocess execution, or streaming).
3. **Artifact Consistency:**
   - Generated images and outputs are written to temporary files, verified, and renamed atomically into the managed artifact directory (`~/OXIMORON/generations/`).
   - The database record is committed immediately after. If a crash occurs between write and DB commit, startup reconciliation links orphan files.

## Consequences
- Clean separation of concerns: users can inspect and tweak operational settings in simple YAML, while application data benefits from ACID properties, indexes, and migrations.
