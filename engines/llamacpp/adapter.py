import asyncio
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import httpx

from core.config.models import EngineInstanceConfig
from core.contracts.enums import ModelFormat
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    EngineCapabilities,
    EngineDescriptor,
    LaunchSpec,
)
from core.logging.logger import OximoronLogger
from engines.base.adapter import BaseEngineAdapter

logger = OximoronLogger("llamacpp_adapter")

class LlamaCppAdapter(BaseEngineAdapter):
    @property
    def adapter_key(self) -> str:
        return "llamacpp"

    @property
    def display_name(self) -> str:
        return "llama.cpp Server"

    async def detect(self, search_roots: list[Path]) -> list[EngineDescriptor]:
        candidates: list[EngineDescriptor] = []
        possible_rel_paths = [
            Path("llama.cpp/build/bin/llama-server"),
            Path("llama-server"),
            Path("build/bin/llama-server"),
            Path(".local/bin/llama-server"),
        ]

        for root in search_roots:
            for rel in possible_rel_paths:
                candidate_path = root / rel
                if candidate_path.exists() and os.access(str(candidate_path), os.X_OK):
                    caps = await self.get_capabilities(EngineInstanceConfig(executable=str(candidate_path)))
                    candidates.append(
                        EngineDescriptor(
                            adapter_key=self.adapter_key,
                            display_name=f"llama.cpp ({candidate_path.parent.parent.name})",
                            config_key="llamacpp",
                            capabilities=caps,
                        )
                    )
        return candidates

    async def validate(self, config: EngineInstanceConfig) -> tuple[bool, str | None]:
        if not config.executable:
            return False, "Executable path not specified"
        path = Path(config.executable)
        if not path.exists():
            return False, f"Executable not found: {config.executable}"
        if not os.access(str(path), os.X_OK):
            return False, f"File is not executable: {config.executable}"
        return True, None

    async def get_capabilities(self, config: EngineInstanceConfig | None) -> EngineCapabilities:
        return EngineCapabilities(
            tasks=["chat", "completion", "embeddings"],
            supported_formats=[ModelFormat.GGUF],
            streaming=True,
            vision=False,
            embeddings=True,
            tool_calling=False,
            concurrency_limit=4,
            can_unload=True,
            supports_cancellation=True,
            notes="llama-server with OpenAI-compatible /v1/chat/completions",
        )

    async def build_launch_spec(
        self,
        config: EngineInstanceConfig,
        model_path: str | None,
        port: int,
    ) -> LaunchSpec:
        if not config.executable:
            raise OximoronException(
                code=ErrorCode.ENGINE_NOT_CONFIGURED,
                message="Executable path not specified for llama.cpp",
                status_code=400,
            )

        args = [
            "--host", "127.0.0.1",
            "--port", str(port),
        ]

        if model_path:
            args.extend(["-m", str(model_path)])
            # Use GPU layers if available
            args.extend(["-ngl", "99"])
            args.extend(["-c", "4096"])

        return LaunchSpec(
            executable=config.executable,
            arguments=args,
            working_directory=str(Path(config.executable).parent),
            port=port,
            host="127.0.0.1",
            ready_probe_path="/health",
            startup_timeout_seconds=config.startup_timeout_seconds,
        )

    async def health_probe(self, endpoint: str) -> tuple[bool, dict[str, Any]]:
        health_url = f"{endpoint}/health"
        async with httpx.AsyncClient(timeout=2.0) as client:
            try:
                resp = await client.get(health_url)
                if resp.status_code == 200:
                    data = resp.json()
                    status_val = data.get("status")
                    if status_val == "ok":
                        return True, data
                    elif status_val == "loading model":
                        return False, {"status": "loading", "data": data}
                    return True, data
                return False, {"status_code": resp.status_code}
            except Exception as e:
                return False, {"error": str(e)}

    async def chat(
        self,
        endpoint: str,
        messages: list[dict[str, str]],
        options: dict[str, Any],
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[str, None]:
        url = f"{endpoint}/v1/chat/completions"
        payload = {
            "messages": messages,
            "stream": True,
            "temperature": options.get("temperature", 0.7),
            "top_p": options.get("top_p", 0.9),
        }
        if "max_tokens" in options and options["max_tokens"]:
            payload["max_tokens"] = options["max_tokens"]

        timeout = httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise OximoronException(
                        code=ErrorCode.INTERNAL_ERROR,
                        message=f"llama-server error {response.status_code}: {error_text.decode('utf-8', errors='replace')}",
                        status_code=502,
                    )

                async for line in response.aiter_lines():
                    if cancel_event and cancel_event.is_set():
                        break
                    line = line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data_part = line.removeprefix("data: ").strip()
                        if data_part == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data_part)
                            choices = parsed.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
