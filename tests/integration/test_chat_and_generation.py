from pathlib import Path

import pytest

from core.contracts.enums import MessageRole, MessageStatus
from core.contracts.models import ChatRequest, ImageGenerationRequest
from core.events.broadcaster import EventBroadcaster
from core.jobs.manager import JobManager
from core.persistence.database import DatabaseManager
from core.services.chat_service import ChatService
from core.services.generation_service import GenerationService
from engines.base.fake import FakeEngineAdapter
from engines.base.registry import AdapterRegistry


@pytest.mark.asyncio
async def test_chat_service_streaming_and_persistence(tmp_path: Path):
    db_file = tmp_path / "test_chat.db"
    db = DatabaseManager(db_path=db_file)
    await db.initialize()

    broadcaster = EventBroadcaster("inst-test")
    job_mgr = JobManager(db, broadcaster)

    fake_adapter = FakeEngineAdapter(
        key="llamacpp",
        chat_tokens=["Hello", " world", " from", " test!"],
    )
    registry = AdapterRegistry()
    registry.register(fake_adapter)

    chat_svc = ChatService(db, job_mgr, registry)

    # 1. Create conversation
    conv = await chat_svc.create_conversation(title="Test Convo", system_prompt="You are helpful.")
    assert conv.id
    assert conv.title == "Test Convo"

    # 2. Stream chat
    req = ChatRequest(
        conversation_id=conv.id,
        message="What is OXIMORON?",
        stream=True,
    )

    deltas = []
    async for chunk in chat_svc.stream_chat(req):
        if chunk.startswith("data: {"):
            deltas.append(chunk)

    assert len(deltas) == 4

    # 3. Verify conversation and messages in DB
    reloaded_conv = await chat_svc.get_conversation(conv.id)
    assert len(reloaded_conv.messages) == 2
    assert reloaded_conv.messages[0].role == MessageRole.USER
    assert reloaded_conv.messages[0].content == "What is OXIMORON?"
    assert reloaded_conv.messages[1].role == MessageRole.ASSISTANT
    assert reloaded_conv.messages[1].content == "Hello world from test!"
    assert reloaded_conv.messages[1].status == MessageStatus.COMPLETED

    await db.close()

@pytest.mark.asyncio
async def test_generation_service_artifact_saving(tmp_path: Path):
    db_file = tmp_path / "test_gen.db"
    db = DatabaseManager(db_path=db_file)
    await db.initialize()

    broadcaster = EventBroadcaster("inst-test")
    job_mgr = JobManager(db, broadcaster)

    # Fake Forge adapter returning a 1x1 base64 png
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    fake_forge = FakeEngineAdapter(key="forge")
    async def mock_gen(endpoint, req, cancel_event=None):
        return {
            "status": "success",
            "seed": 1234,
            "images": [tiny_png_b64],
            "parameters": {"prompt": req.prompt},
        }
    fake_forge.generate_image = mock_gen

    registry = AdapterRegistry()
    registry.register(fake_forge)

    gen_dir = tmp_path / "generations"
    gen_svc = GenerationService(db, job_mgr, registry, artifact_dir=gen_dir)

    req = ImageGenerationRequest(
        prompt="A photo of a cat driving a WagonR",
        width=512,
        height=512,
        seed=1234,
    )

    gen = await gen_svc.generate_image(req)
    assert gen.seed == 1234
    assert len(gen.artifacts) == 1
    assert Path(gen.artifacts[0].absolute_path).exists()
    assert Path(gen.artifacts[0].absolute_path).stat().st_size > 0

    # Verify list generations
    history = await gen_svc.list_generations()
    assert len(history) == 1
    assert history[0].prompt == "A photo of a cat driving a WagonR"

    await db.close()
