from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps.backend.dependencies import verify_bearer_token
from core.contracts.models import ConversationDescriptor
from core.services.chat_service import ChatService

router = APIRouter(prefix="/conversations", tags=["Conversations"])

class CreateConversationRequest(BaseModel):
    title: str = "New Conversation"
    system_prompt: str | None = None

def get_chat_service(request) -> ChatService:
    return request.app.state.chat_service

@router.get("", response_model=list[ConversationDescriptor])
async def list_conversations(
    _token: str = Depends(verify_bearer_token),
    chat_svc: ChatService = Depends(get_chat_service),
    limit: int = Query(default=50, ge=1, le=100),
):
    return await chat_svc.list_conversations(limit=limit)

@router.post("", response_model=ConversationDescriptor)
async def create_conversation(
    req: CreateConversationRequest,
    _token: str = Depends(verify_bearer_token),
    chat_svc: ChatService = Depends(get_chat_service),
):
    return await chat_svc.create_conversation(title=req.title, system_prompt=req.system_prompt)

@router.get("/{conversation_id}", response_model=ConversationDescriptor)
async def get_conversation(
    conversation_id: str,
    _token: str = Depends(verify_bearer_token),
    chat_svc: ChatService = Depends(get_chat_service),
):
    return await chat_svc.get_conversation(conversation_id)
