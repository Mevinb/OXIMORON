import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from core.config.models import EngineInstanceConfig
from core.contracts.models import (
    EngineCapabilities,
    EngineDescriptor,
    ImageGenerationRequest,
    LaunchSpec,
)


class BaseEngineAdapter(ABC):
    @property
    @abstractmethod
    def adapter_key(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        pass

    @abstractmethod
    async def detect(self, search_roots: list[Path]) -> list[EngineDescriptor]:
        """Read-only detection of engine candidates in approved search roots without execution."""
        pass

    @abstractmethod
    async def validate(self, config: EngineInstanceConfig) -> tuple[bool, str | None]:
        """Validate paths, binaries, and dependencies without side effects."""
        pass

    @abstractmethod
    async def get_capabilities(self, config: EngineInstanceConfig) -> EngineCapabilities:
        """Return versioned static/probed capabilities without model inference."""
        pass

    @abstractmethod
    async def build_launch_spec(
        self,
        config: EngineInstanceConfig,
        model_path: str | None,
        port: int,
    ) -> LaunchSpec:
        """Build argument array, working directory, and sanitized environment."""
        pass

    @abstractmethod
    async def health_probe(self, endpoint: str) -> tuple[bool, dict[str, Any]]:
        """Probe engine readiness endpoint."""
        pass

    async def load_model(self, endpoint: str, model_path: str) -> bool:
        """Explicit model load where supported. Raises NotImplementedError if not supported."""
        raise NotImplementedError(f"Model loading via API is not supported by {self.adapter_key}")

    async def unload_model(self, endpoint: str) -> bool:
        """Explicit model unload where supported. Raises NotImplementedError if not supported."""
        raise NotImplementedError(f"Model unloading via API is not supported by {self.adapter_key}")

    async def chat(
        self,
        endpoint: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat delta tokens."""
        if False:
            yield ""
        raise NotImplementedError(f"Chat is not supported by {self.adapter_key}")

    async def generate_image(
        self,
        endpoint: str,
        request: ImageGenerationRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        """Generate image and return output metadata."""
        raise NotImplementedError(f"Image generation is not supported by {self.adapter_key}")

    async def cancel(self, endpoint: str, request_id: str) -> bool:
        """Cancel an in-flight operation if supported by engine."""
        return False
