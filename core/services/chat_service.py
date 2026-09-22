import json
from collections.abc import AsyncGenerator

from sqlalchemy import select

from core.contracts.enums import JobKind, JobState, MessageRole, MessageStatus
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    ChatRequest,
    ConversationDescriptor,
    MessageDescriptor,
    gen_uuid,
    utc_now,
)
from core.jobs.manager import JobManager
from core.logging.logger import OximoronLogger
from core.persistence.database import DatabaseManager
from core.persistence.models import ConversationModel, EngineModel, MessageModel
from engines.base.registry import AdapterRegistry

logger = OximoronLogger("chat_service")

class ChatService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        job_manager: JobManager,
        adapter_registry: AdapterRegistry,
    ):
        self.db = db_manager
        self.jobs = job_manager
        self.adapters = adapter_registry

    async def list_conversations(self, limit: int = 50) -> list[ConversationDescriptor]:
        async with self.db.session() as session:
            stmt = select(ConversationModel).order_by(ConversationModel.updated_at.desc()).limit(limit)
            res = await session.execute(stmt)
            convs = res.scalars().all()
            return [
                ConversationDescriptor(
                    id=c.id,
                    workspace_id=c.workspace_id,
                    title=c.title,
                    default_model_id=c.default_model_id,
                    system_prompt=c.system_prompt,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in convs
            ]

    async def get_conversation(self, conversation_id: str) -> ConversationDescriptor:
        async with self.db.session() as session:
            stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
            res = await session.execute(stmt)
            c = res.scalar_one_or_none()
            if not c:
                raise OximoronException(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Conversation {conversation_id} not found",
                    status_code=404,
                )

            # Get messages ordered by sequence
            msg_stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id).order_by(MessageModel.sequence.asc())
            msg_res = await session.execute(msg_stmt)
            messages = [
                MessageDescriptor(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    sequence=m.sequence,
                    role=MessageRole(m.role),
                    content=m.content,
                    status=MessageStatus(m.status),
                    model_id=m.model_id,
                    tokens_in=m.tokens_in,
                    tokens_out=m.tokens_out,
                    created_at=m.created_at,
                )
                for m in msg_res.scalars().all()
            ]

            return ConversationDescriptor(
                id=c.id,
                workspace_id=c.workspace_id,
                title=c.title,
                default_model_id=c.default_model_id,
                system_prompt=c.system_prompt,
                created_at=c.created_at,
                updated_at=c.updated_at,
                messages=messages,
            )

    async def create_conversation(self, title: str = "New Conversation", system_prompt: str | None = None) -> ConversationDescriptor:
        conv_id = gen_uuid()
        async with self.db.session() as session:
            model = ConversationModel(
                id=conv_id,
                title=title,
                system_prompt=system_prompt,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(model)

        return ConversationDescriptor(
            id=conv_id,
            title=title,
            system_prompt=system_prompt,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
    ) -> AsyncGenerator[str, None]:
        # 1. Ensure conversation exists
        conv_id = request.conversation_id
        if not conv_id:
            new_conv = await self.create_conversation(title=request.message[:40])
            conv_id = new_conv.id

        # 2. Append User Message
        user_msg_id = gen_uuid()
        asst_msg_id = gen_uuid()

        async with self.db.session() as session:
            seq_stmt = select(MessageModel.sequence).where(MessageModel.conversation_id == conv_id).order_by(MessageModel.sequence.desc())
            seq_res = await session.execute(seq_stmt)
            last_seq = seq_res.scalars().first() or 0

            user_msg = MessageModel(
                id=user_msg_id,
                conversation_id=conv_id,
                sequence=last_seq + 1,
                role=MessageRole.USER.value,
                content=request.message,
                status=MessageStatus.COMPLETED.value,
                created_at=utc_now(),
            )
            session.add(user_msg)

            asst_msg = MessageModel(
                id=asst_msg_id,
                conversation_id=conv_id,
                sequence=last_seq + 2,
                role=MessageRole.ASSISTANT.value,
                content="",
                status=MessageStatus.STREAMING.value,
                created_at=utc_now(),
            )
            session.add(asst_msg)

        # 3. Create Job
        job = await self.jobs.create_job(
            kind=JobKind.CHAT,
            engine_id=request.engine_id,
            model_id=request.model_id,
            request_snapshot={"conversation_id": conv_id, "message": request.message},
        )
        cancel_event = self.jobs.get_cancel_event(job.id)

        # 4. Resolve active engine endpoint
        endpoint = None
        adapter_key = "llamacpp"
        if request.engine_id:
            async with self.db.session() as session:
                stmt = select(EngineModel).where(EngineModel.id == request.engine_id)
                res = await session.execute(stmt)
                eng = res.scalar_one_or_none()
                if eng and eng.endpoint:
                    endpoint = eng.endpoint
                    adapter_key = eng.adapter_key

        if not endpoint:
            # Fallback to local default llama-server endpoint
            endpoint = "http://127.0.0.1:8080"

        adapter = self.adapters.get(adapter_key)

        # 5. Build conversation history
        conv = await self.get_conversation(conv_id)
        history = []
        if conv.system_prompt:
            history.append({"role": "system", "content": conv.system_prompt})
        for m in conv.messages[:-1]:  # exclude pending assistant msg
            history.append({"role": m.role.value, "content": m.content})

        accumulated_text = ""
        await self.jobs.update_job_state(job.id, JobState.RUNNING)

        try:
            # Stream tokens
            async for delta in adapter.chat(
                endpoint=endpoint,
                messages=history,
                options={"temperature": request.temperature, "top_p": request.top_p, "max_tokens": request.max_tokens},
                cancel_event=cancel_event,
            ):
                accumulated_text += delta
                chunk = json.dumps({"delta": delta, "job_id": job.id, "conversation_id": conv_id})
                yield f"data: {chunk}\n\n"

            # Finalize message in DB
            async with self.db.session() as session:
                stmt = select(MessageModel).where(MessageModel.id == asst_msg_id)
                res = await session.execute(stmt)
                m = res.scalar_one()
                m.content = accumulated_text
                m.status = MessageStatus.COMPLETED.value if not cancel_event.is_set() else MessageStatus.CANCELLED.value

            final_state = JobState.SUCCEEDED if not cancel_event.is_set() else JobState.CANCELLED
            await self.jobs.update_job_state(job.id, final_state, outcome={"tokens_out": len(accumulated_text.split())})
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Chat streaming error: {e}")
            async with self.db.session() as session:
                stmt = select(MessageModel).where(MessageModel.id == asst_msg_id)
                res = await session.execute(stmt)
                m = res.scalar_one_or_none()
                if m:
                    m.content = accumulated_text
                    m.status = MessageStatus.ERROR.value

            await self.jobs.update_job_state(job.id, JobState.FAILED, error_code=ErrorCode.INTERNAL_ERROR, error_message=str(e))
            err_chunk = json.dumps({"error": str(e), "job_id": job.id})
            yield f"data: {err_chunk}\n\n"
