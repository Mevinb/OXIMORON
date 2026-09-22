import asyncio
from pathlib import Path
from typing import Any

import httpx

from core.config.models import EngineInstanceConfig
from core.contracts.enums import ModelFormat
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    EngineCapabilities,
    EngineDescriptor,
    ImageGenerationRequest,
    LaunchSpec,
)
from core.logging.logger import OximoronLogger
from engines.base.adapter import BaseEngineAdapter

logger = OximoronLogger("fooocus_adapter")

class FooocusAdapter(BaseEngineAdapter):
    @property
    def adapter_key(self) -> str:
        return "fooocus"

    @property
    def display_name(self) -> str:
        return "Fooocus"

    async def detect(self, search_roots: list[Path]) -> list[EngineDescriptor]:
        candidates: list[EngineDescriptor] = []
        possible_dirs = [
            Path("Data/foocus"),
            Path("foocus"),
            Path("Fooocus"),
        ]

        for root in search_roots:
            for rel in possible_dirs:
                candidate_dir = root / rel
                entry_file = candidate_dir / "entry_with_update.py"
                venv_python = candidate_dir / "fooocus_env" / "bin" / "python"
                if candidate_dir.exists() and (entry_file.exists() or (candidate_dir / "launch.py").exists()):
                    py_exe = str(venv_python) if venv_python.exists() else None
                    caps = await self.get_capabilities(EngineInstanceConfig(directory=str(candidate_dir), python_executable=py_exe))
                    candidates.append(
                        EngineDescriptor(
                            adapter_key=self.adapter_key,
                            display_name=f"Fooocus ({candidate_dir.name})",
                            config_key="fooocus",
                            capabilities=caps,
                        )
                    )
        return candidates

    async def validate(self, config: EngineInstanceConfig) -> tuple[bool, str | None]:
        if not config.directory:
            return False, "Fooocus directory not configured"
        dir_path = Path(config.directory)
        if not dir_path.exists():
            return False, f"Directory not found: {config.directory}"
        entry = dir_path / "entry_with_update.py"
        if not entry.exists():
            return False, f"entry_with_update.py not found in {config.directory}"
        return True, None

    async def get_capabilities(self, config: EngineInstanceConfig | None) -> EngineCapabilities:
        return EngineCapabilities(
            tasks=["lifecycle"],
            supported_formats=[ModelFormat.SAFETENSORS],
            streaming=False,
            vision=False,
            can_unload=True,
            supports_cancellation=False,
            notes="Lifecycle support only. Integrated generation unsupported until official bridge validated.",
        )

    async def build_launch_spec(
        self,
        config: EngineInstanceConfig,
        model_path: str | None,
        port: int,
    ) -> LaunchSpec:
        if not config.directory:
            raise OximoronException(
                code=ErrorCode.ENGINE_NOT_CONFIGURED,
                message="Fooocus directory not configured",
                status_code=400,
            )

        python_bin = config.python_executable or "python3"
        entry_file = str(Path(config.directory) / "entry_with_update.py")

        args = [
            entry_file,
            "--listen", "127.0.0.1",
            "--port", str(port),
        ]

        return LaunchSpec(
            executable=python_bin,
            arguments=args,
            working_directory=config.directory,
            port=port,
            host="127.0.0.1",
            ready_probe_path="/",
            startup_timeout_seconds=config.startup_timeout_seconds,
        )

    async def health_probe(self, endpoint: str) -> tuple[bool, dict[str, Any]]:
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.get(endpoint)
                return resp.status_code in [200, 302, 307], {"status_code": resp.status_code}
            except Exception as e:
                return False, {"error": str(e)}

    async def generate_image(
        self,
        endpoint: str,
        request: ImageGenerationRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        raise OximoronException(
            code=ErrorCode.ENGINE_UNSUPPORTED,
            message="Integrated generation with Fooocus is unsupported in v0.1. Use WebUI directly or use Forge.",
            status_code=400,
        )
