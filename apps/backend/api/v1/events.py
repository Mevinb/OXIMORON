import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from apps.backend.dependencies import get_event_broadcaster, verify_bearer_token
from core.events.broadcaster import EventBroadcaster

router = APIRouter(tags=["Events & WebSocket"])

class TicketResponse(BaseModel):
    ticket: str
    expires_in_seconds: int = 30

@router.post("/events/ticket", response_model=TicketResponse)
async def create_event_ticket(
    _token: str = Depends(verify_bearer_token),
    broadcaster: EventBroadcaster = Depends(get_event_broadcaster),
):
    ticket = broadcaster.create_ticket()
    return TicketResponse(ticket=ticket, expires_in_seconds=30)

@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
):
    await websocket.accept()
    broadcaster: EventBroadcaster = websocket.app.state.event_broadcaster

    # Step 1: Ticket authentication within 5 seconds
    try:
        raw_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        # Parse ticket or JSON containing ticket
        ticket_str = raw_msg.strip().strip('"')
        if not broadcaster.validate_and_consume_ticket(ticket_str):
            await websocket.send_json({"error": "INVALID_TICKET", "message": "Ticket invalid or expired"})
            await websocket.close(code=4001)
            return
    except (TimeoutError, Exception):
        try:
            await websocket.send_json({"error": "AUTH_TIMEOUT", "message": "Ticket not received in time"})
            await websocket.close(code=4002)
        except Exception:
            pass
        return

    # Step 2: Subscribe and stream events
    queue = await broadcaster.subscribe(max_queue_size=256)
    try:
        await websocket.send_json({"type": "connection.ready", "status": "authenticated"})
        while True:
            try:
                # Wait for next event or send heartbeat every 15 seconds
                envelope = await asyncio.wait_for(queue.get(), timeout=15.0)
                await websocket.send_json(envelope.model_dump(mode="json"))
            except TimeoutError:
                # Heartbeat
                await websocket.send_json({"type": "heartbeat"})
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        await broadcaster.unsubscribe(queue)
