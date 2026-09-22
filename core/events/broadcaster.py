import asyncio
import secrets
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from core.contracts.models import EventEnvelope, gen_uuid, utc_now


class WebSocketTicket(BaseModel):
    ticket: str
    created_at: datetime = Field(default_factory=utc_now)
    ttl_seconds: int = 30

class EventBroadcaster:
    def __init__(self, supervisor_instance_id: str):
        self.supervisor_instance_id = supervisor_instance_id
        self._sequence = 0
        self._subscribers: set[asyncio.Queue] = set()
        self._tickets: dict[str, WebSocketTicket] = {}
        self._lock = asyncio.Lock()

    def create_ticket(self) -> str:
        ticket_str = secrets.token_urlsafe(24)
        now = datetime.now(UTC)
        # Purge expired tickets
        self._tickets = {
            t: data for t, data in self._tickets.items()
            if (now - data.created_at).total_seconds() < data.ttl_seconds
        }
        self._tickets[ticket_str] = WebSocketTicket(ticket=ticket_str, created_at=now)
        return ticket_str

    def validate_and_consume_ticket(self, ticket_str: str) -> bool:
        ticket = self._tickets.pop(ticket_str, None)
        if not ticket:
            return False
        age = (datetime.now(UTC) - ticket.created_at).total_seconds()
        return age <= ticket.ttl_seconds

    async def subscribe(self, max_queue_size: int = 256) -> asyncio.Queue[EventEnvelope]:
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=max_queue_size)
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[EventEnvelope]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)

    async def broadcast(
        self,
        event_type: str,
        payload: dict[str, Any],
        job_id: str | None = None,
        entity_id: str | None = None,
    ) -> EventEnvelope:
        async with self._lock:
            self._sequence += 1
            seq = self._sequence
            envelope = EventEnvelope(
                event_id=gen_uuid(),
                supervisor_instance_id=self.supervisor_instance_id,
                sequence=seq,
                job_id=job_id,
                entity_id=entity_id,
                type=event_type,
                timestamp=datetime.now(UTC),
                payload=payload,
            )
            # Deliver to subscribers without blocking if full
            subscribers_snapshot = list(self._subscribers)

        for q in subscribers_snapshot:
            try:
                q.put_nowait(envelope)
            except asyncio.QueueFull:
                # Discard oldest or drop if slow consumer
                try:
                    q.get_nowait()
                    q.put_nowait(envelope)
                except Exception:
                    pass

        return envelope
