import asyncio
import os
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

logger = OximoronLogger("forge_adapter")

class ForgeAdapter(BaseEngineAdapter):
    @property
    def adapter_key(self) -> str:
        return "forge"

    @property
    def display_name(self) -> str:
        return "Stable Diffusion WebUI Forge"

    async def detect(self, search_roots: list[Path]) -> list[EngineDescriptor]:
        candidates: list[EngineDescriptor] = []
        possible_dirs = [
            Path("Data/forge/stable-diffusion-webui-forge"),
            Path("stable-diffusion-webui-forge"),
            Path("forge/stable-diffusion-webui-forge"),
        ]

        for root in search_roots:
            for rel in possible_dirs:
                candidate_dir = root / rel
                launch_file = candidate_dir / "launch.py"
                venv_python = candidate_dir / "venv" / "bin" / "python"
                if candidate_dir.exists() and launch_file.exists():
                    py_exe = str(venv_python) if venv_python.exists() else None
                    caps = await self.get_capabilities(EngineInstanceConfig(directory=str(candidate_dir), python_executable=py_exe))
                    candidates.append(
                        EngineDescriptor(
                            adapter_key=self.adapter_key,
                            display_name=f"Forge ({candidate_dir.name})",
                            config_key="forge",
                            capabilities=caps,
                        )
                    )
        return candidates

    async def validate(self, config: EngineInstanceConfig) -> tuple[bool, str | None]:
        if not config.directory:
            return False, "Forge directory not specified"
        dir_path = Path(config.directory)
        if not dir_path.exists():
            return False, f"Directory not found: {config.directory}"
        launch_py = dir_path / "launch.py"
        if not launch_py.exists():
            return False, f"launch.py not found in {config.directory}"
        if config.python_executable:
            py_path = Path(config.python_executable)
            if not py_path.exists() or not os.access(str(py_path), os.X_OK):
                return False, f"Python interpreter not executable: {config.python_executable}"
        return True, None

    async def get_capabilities(self, config: EngineInstanceConfig | None) -> EngineCapabilities:
        return EngineCapabilities(
            tasks=["txt2img", "img2img", "inpaint"],
            supported_formats=[ModelFormat.SAFETENSORS, ModelFormat.CKPT, ModelFormat.GGUF],
            streaming=False,
            vision=True,
            can_unload=True,
            supports_cancellation=True,
            notes="WebUI Forge with SDAPI v1 REST endpoints",
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
                message="Forge directory not configured",
                status_code=400,
            )

        python_bin = config.python_executable or "python3"
        launch_file = str(Path(config.directory) / "launch.py")

        args = [
            launch_file,
            "--api",
            "--nowebui",
            "--port", str(port),
            "--skip-load-model-at-start",
        ]

        return LaunchSpec(
            executable=python_bin,
            arguments=args,
            working_directory=config.directory,
            port=port,
            host="127.0.0.1",
            ready_probe_path="/sdapi/v1/progress",
            startup_timeout_seconds=config.startup_timeout_seconds,
        )

    async def health_probe(self, endpoint: str) -> tuple[bool, dict[str, Any]]:
        url = f"{endpoint}/sdapi/v1/progress"
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return True, resp.json()
                return False, {"status_code": resp.status_code}
            except Exception as e:
                return False, {"error": str(e)}

    async def list_models(self, endpoint: str) -> list[dict[str, Any]]:
        url = f"{endpoint}/sdapi/v1/sd-models"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
            return []

    async def generate_image(
        self,
        endpoint: str,
        request: ImageGenerationRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> dict[str, Any]:
        url = f"{endpoint}/sdapi/v1/txt2img"
        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "sampler_name": request.sampler_name,
            "seed": request.seed,
            "batch_size": request.batch_count,
        }

        timeout = httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            task = asyncio.create_task(client.post(url, json=payload))

            while not task.done():
                if cancel_event and cancel_event.is_set():
                    await self.cancel(endpoint, "active_txt2img")
                    task.cancel()
                    return {"status": "cancelled"}
                await asyncio.sleep(0.5)

            resp = await task
            if resp.status_code != 200:
                raise OximoronException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Forge generation failed ({resp.status_code}): {resp.text[:200]}",
                    status_code=502,
                )

            data = resp.json()
            return {
                "status": "success",
                "images": data.get("images", []),
                "parameters": data.get("parameters", {}),
                "info": data.get("info", ""),
            }

    async def cancel(self, endpoint: str, request_id: str) -> bool:
        url = f"{endpoint}/sdapi/v1/interrupt"
        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                resp = await client.post(url)
                return resp.status_code == 200
            except Exception:
                return False
