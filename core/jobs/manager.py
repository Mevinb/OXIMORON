import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from core.contracts.enums import JobKind, JobState
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import JobDescriptor, gen_uuid, utc_now
from core.events.broadcaster import EventBroadcaster
from core.persistence.database import DatabaseManager
from core.persistence.models import IdempotencyKeyModel, JobEventModel, JobModel


class JobManager:
    def __init__(self, db_manager: DatabaseManager, broadcaster: EventBroadcaster):
        self.db = db_manager
        self.broadcaster = broadcaster
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    def get_cancel_event(self, job_id: str) -> asyncio.Event:
        if job_id not in self._cancel_events:
            self._cancel_events[job_id] = asyncio.Event()
        return self._cancel_events[job_id]

    async def check_idempotency(
        self,
        scope: str,
        operation: str,
        idempotency_key: str,
        payload: dict[str, Any],
    ) -> str | None:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        async with self.db.session() as session:
            stmt = select(IdempotencyKeyModel).where(
                IdempotencyKeyModel.scope == scope,
                IdempotencyKeyModel.operation == operation,
                IdempotencyKeyModel.key_hash == key_hash,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                if existing.payload_hash != payload_hash:
                    raise OximoronException(
                        code=ErrorCode.CONFLICT,
                        message="Idempotency key reuse with different request payload.",
                        status_code=409,
                    )
                return existing.job_id

            return None

    async def register_idempotency(
        self,
        scope: str,
        operation: str,
        idempotency_key: str,
        payload: dict[str, Any],
        job_id: str,
    ) -> None:
        key_hash = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        payload_str = json.dumps(payload, sort_keys=True)
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        async with self.db.session() as session:
            key_record = IdempotencyKeyModel(
                scope=scope,
                operation=operation,
                key_hash=key_hash,
                payload_hash=payload_hash,
                job_id=job_id,
                expires_at=expires_at,
            )
            session.add(key_record)

    async def create_job(
        self,
        kind: JobKind,
        workspace_id: str = "default",
        engine_id: str | None = None,
        model_id: str | None = None,
        request_snapshot: dict[str, Any] | None = None,
    ) -> JobDescriptor:
        job_id = gen_uuid()
        self.get_cancel_event(job_id)

        async with self.db.session() as session:
            job_entity = JobModel(
                id=job_id,
                kind=kind.value,
                workspace_id=workspace_id,
                engine_id=engine_id,
                model_id=model_id,
                state=JobState.QUEUED.value,
                request_snapshot=request_snapshot or {},
                created_at=utc_now(),
            )
            session.add(job_entity)

            # Record initial state event
            event = JobEventModel(
                job_id=job_id,
                sequence=1,
                event_type="job.state",
                payload_json={"from": None, "to": JobState.QUEUED.value},
                timestamp=utc_now(),
            )
            session.add(event)

        desc = JobDescriptor(
            id=job_id,
            kind=kind,
            state=JobState.QUEUED,
            workspace_id=workspace_id,
            engine_id=engine_id,
            model_id=model_id,
            request_snapshot=request_snapshot or {},
        )

        await self.broadcaster.broadcast(
            event_type="job.state",
            payload={"job_id": job_id, "state": JobState.QUEUED.value},
            job_id=job_id,
        )

        return desc

    async def update_job_state(
        self,
        job_id: str,
        new_state: JobState,
        error_code: str | None = None,
        error_message: str | None = None,
        outcome: dict[str, Any] | None = None,
    ) -> None:
        async with self.db.session() as session:
            stmt = select(JobModel).where(JobModel.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return

            old_state = job.state
            job.state = new_state.value
            now = utc_now()

            if new_state == JobState.RUNNING and not job.started_at:
                job.started_at = now
            elif new_state in [JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED]:
                job.finished_at = now
                if job_id in self._cancel_events:
                    del self._cancel_events[job_id]

            if error_code:
                job.error_code = error_code
            if error_message:
                job.error_message = error_message
            if outcome:
                job.outcome_json = outcome

            # Get next event sequence
            seq_stmt = select(JobEventModel.sequence).where(JobEventModel.job_id == job_id).order_by(JobEventModel.sequence.desc())
            seq_res = await session.execute(seq_stmt)
            last_seq = seq_res.scalars().first() or 0

            event = JobEventModel(
                job_id=job_id,
                sequence=last_seq + 1,
                event_type="job.state",
                payload_json={"from": old_state, "to": new_state.value},
                timestamp=now,
            )
            session.add(event)

        await self.broadcaster.broadcast(
            event_type="job.state",
            payload={
                "job_id": job_id,
                "state": new_state.value,
                "error_code": error_code,
                "error_message": error_message,
            },
            job_id=job_id,
        )

    async def cancel_job(self, job_id: str) -> bool:
        cancel_ev = self._cancel_events.get(job_id)
        if cancel_ev:
            cancel_ev.set()

        async with self.db.session() as session:
            stmt = select(JobModel).where(JobModel.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return False

            if job.state in [JobState.SUCCEEDED.value, JobState.FAILED.value, JobState.CANCELLED.value]:
                return False

            job.cancel_requested_at = utc_now()
            job.state = JobState.CANCEL_REQUESTED.value

        await self.broadcaster.broadcast(
            event_type="job.state",
            payload={"job_id": job_id, "state": JobState.CANCEL_REQUESTED.value},
            job_id=job_id,
        )
        return True

    async def get_job(self, job_id: str) -> JobDescriptor | None:
        async with self.db.session() as session:
            stmt = select(JobModel).where(JobModel.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return None

            return JobDescriptor(
                id=job.id,
                kind=JobKind(job.kind),
                state=JobState(job.state),
                workspace_id=job.workspace_id,
                engine_id=job.engine_id,
                model_id=job.model_id,
                request_snapshot=job.request_snapshot,
                started_at=job.started_at,
                finished_at=job.finished_at,
                cancel_requested_at=job.cancel_requested_at,
                error_code=job.error_code,
                error_message=job.error_message,
                outcome=job.outcome_json,
                created_at=job.created_at,
            )
