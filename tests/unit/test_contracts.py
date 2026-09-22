from core.contracts.enums import EngineState, JobKind, JobState, ModelFormat, ModelRole
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    EngineCapabilities,
    EngineDescriptor,
)


def test_enums_and_descriptors():
    assert EngineState.READY == "ready"
    assert JobState.RUNNING == "running"
    assert JobKind.CHAT == "chat"
    assert ModelFormat.GGUF == "gguf"
    assert ModelRole.LLM == "llm"

def test_engine_descriptor_creation():
    eng = EngineDescriptor(
        adapter_key="llamacpp",
        display_name="llama.cpp Server",
        config_key="llamacpp",
        capabilities=EngineCapabilities(
            tasks=["chat"],
            supported_formats=[ModelFormat.GGUF],
            streaming=True,
        ),
    )
    assert eng.observed_state == EngineState.UNCONFIGURED
    assert eng.capabilities.streaming is True
    assert eng.capabilities.supported_formats == [ModelFormat.GGUF]

def test_oximoron_exception_conversion():
    exc = OximoronException(
        code=ErrorCode.RESOURCE_CONFLICT,
        message="Memory limit exceeded",
        status_code=409,
        details={"vram_needed": 8000},
    )
    detail = exc.to_error_detail(request_id="test-req-123")
    assert detail.code == ErrorCode.RESOURCE_CONFLICT
    assert detail.request_id == "test-req-123"
    assert detail.details["vram_needed"] == 8000
