from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from apps.backend.dependencies import verify_bearer_token
from core.contracts.models import ChatRequest
from core.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])

def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service

@router.post("")
async def submit_chat_message(
    req: ChatRequest,
    _token: str = Depends(verify_bearer_token),
    chat_svc: ChatService = Depends(get_chat_service),
):
    stream = chat_svc.stream_chat(req)
    return StreamingResponse(stream, media_type="text/event-stream")
