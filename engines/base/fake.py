import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from core.config.models import EngineInstanceConfig
from core.contracts.enums import ModelFormat
from core.contracts.models import (
    EngineCapabilities,
    EngineDescriptor,
    ImageGenerationRequest,
    LaunchSpec,
)
from engines.base.adapter import BaseEngineAdapter


class FakeEngineAdapter(BaseEngineAdapter):
    def __init__(
        self,
        key: str = "fake",
        name: str = "Fake Test Engine",
        fail_health: bool = False,
        chat_tokens: list[str] | None = None,
    ):
        self._key = key
        self._name = name
        self.fail_health = fail_health
        self.chat_tokens = chat_tokens or ["Hello", " ", "from", " ", "OXIMORON!"]
        self.cancelled = False

    @property
    def adapter_key(self) -> str:
        return self._key

    @property
    def display_name(self) -> str:
        return self._name

    async def detect(self, search_roots: list[Path]) -> list[EngineDescriptor]:
        return [
            EngineDescriptor(
                adapter_key=self.adapter_key,
                display_name=self.display_name,
                config_key=self.adapter_key,
                capabilities=await self.get_capabilities(EngineInstanceConfig()),
            )
        ]

    async def validate(self, config: EngineInstanceConfig) -> tuple[bool, str | None]:
        return True, None

    async def get_capabilities(self, config: EngineInstanceConfig) -> EngineCapabilities:
        return EngineCapabilities(
            tasks=["chat", "image"],
            supported_formats=[ModelFormat.GGUF, ModelFormat.SAFETENSORS],
            streaming=True,
            can_unload=True,
            supports_cancellation=True,
        )

    async def build_launch_spec(
        self,
        config: EngineInstanceConfig,
        model_path: str | None,
        port: int,
    ) -> LaunchSpec:
        return LaunchSpec(
            executable="/bin/true",
            arguments=["--port", str(port)],
            working_directory="/tmp",
            port=port,
        )

    async def health_probe(self, endpoint: str) -> tuple[bool, dict[str, Any]]:
        if self.fail_health:
            return False, {"error": "Simulated unready state"}
        return True, {"status": "ok", "loaded_model": "test-model"}

    async def chat(
        self,
        endpoint: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[str, None]:
        for token in self.chat_tokens:
            if cancel_event and cancel_event.is_set():
                self.cancelled = True
                break
            await asyncio.sleep(0.01)
            yield token

    async def generate_image(
        self,
        endpoint: str,
        request: ImageGenerationRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        if cancel_event and cancel_event.is_set():
            self.cancelled = True
            return {"status": "cancelled"}
        return {
            "status": "success",
            "seed": 42 if request.seed == -1 else request.seed,
            "width": request.width,
            "height": request.height,
            "images": ["fake_base64_or_path"],
        }

    async def cancel(self, endpoint: str, request_id: str) -> bool:
        self.cancelled = True
        return True
