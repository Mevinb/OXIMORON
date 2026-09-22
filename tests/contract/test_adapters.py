import pytest

from core.config.models import EngineInstanceConfig
from core.contracts.enums import ModelFormat
from core.contracts.errors import OximoronException
from core.contracts.models import ImageGenerationRequest
from engines.base.fake import FakeEngineAdapter
from engines.fooocus.adapter import FooocusAdapter
from engines.forge.adapter import ForgeAdapter
from engines.llamacpp.adapter import LlamaCppAdapter


@pytest.mark.asyncio
async def test_fake_adapter_contract():
    adapter = FakeEngineAdapter()
    assert adapter.adapter_key == "fake"

    caps = await adapter.get_capabilities(EngineInstanceConfig())
    assert caps.streaming is True
    assert ModelFormat.GGUF in caps.supported_formats

    spec = await adapter.build_launch_spec(EngineInstanceConfig(), "/tmp/model.gguf", 8080)
    assert spec.executable == "/bin/true"
    assert spec.port == 8080

    is_ready, details = await adapter.health_probe("http://127.0.0.1:8080")
    assert is_ready is True

@pytest.mark.asyncio
async def test_llamacpp_adapter_launch_spec():
    adapter = LlamaCppAdapter()
    config = EngineInstanceConfig(
        executable="/home/mevlec/llama.cpp/build/bin/llama-server",
        preferred_port=8080,
    )

    spec = await adapter.build_launch_spec(config, "/models/test.gguf", 8080)
    assert spec.executable == "/home/mevlec/llama.cpp/build/bin/llama-server"
    assert "--port" in spec.arguments
    assert "8080" in spec.arguments
    assert "-m" in spec.arguments
    assert "/models/test.gguf" in spec.arguments
    assert "--host" in spec.arguments
    assert "127.0.0.1" in spec.arguments

@pytest.mark.asyncio
async def test_forge_adapter_launch_spec():
    adapter = ForgeAdapter()
    config = EngineInstanceConfig(
        directory="/home/mevlec/Data/forge/stable-diffusion-webui-forge",
        python_executable="/home/mevlec/Data/forge/stable-diffusion-webui-forge/venv/bin/python",
        preferred_port=7860,
    )

    spec = await adapter.build_launch_spec(config, None, 7860)
    assert spec.executable == config.python_executable
    assert "--api" in spec.arguments
    assert "--nowebui" in spec.arguments
    assert "--port" in spec.arguments
    assert "7860" in spec.arguments

@pytest.mark.asyncio
async def test_fooocus_adapter_rejects_integrated_generation():
    adapter = FooocusAdapter()
    req = ImageGenerationRequest(prompt="test prompt")

    with pytest.raises(OximoronException) as exc_info:
        await adapter.generate_image("http://127.0.0.1:7865", req)
    assert "unsupported in v0.1" in exc_info.value.message.lower()
