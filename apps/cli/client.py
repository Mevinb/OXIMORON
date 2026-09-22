import json
from pathlib import Path
from typing import Any

import httpx

from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import RuntimeDiscoveryRecord
from core.secrets.manager import SecretManager
from core.supervisor.lock import DEFAULT_DISCOVERY_PATH


class OximoronClient:
    def __init__(self, discovery_path: Path | None = None):
        self.discovery_path = discovery_path or DEFAULT_DISCOVERY_PATH
        self.base_url: str | None = None
        self.token: str | None = None
        self._attach()

    def _attach(self) -> None:
        if not self.discovery_path.exists():
            raise OximoronException(
                code=ErrorCode.INTERNAL_ERROR,
                message="OXIMORON backend is not running. Please start it with 'oximoron-backend'.",
                status_code=503,
            )

        with open(self.discovery_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        discovery = RuntimeDiscoveryRecord.model_validate(data)
        self.base_url = discovery.base_url

        # Read credentials
        secret_mgr = SecretManager(credential_path=Path(discovery.credential_file))
        self.token = secret_mgr.get_or_create_token()

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            resp = client.get(url, headers=self._get_headers(), params=params)
            if resp.status_code >= 400:
                raise OximoronException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"API Error ({resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                )
            return resp.json()

    def post(self, path: str, json_data: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=30.0, follow_redirects=False) as client:
            resp = client.post(url, headers=self._get_headers(), json=json_data)
            if resp.status_code >= 400:
                raise OximoronException(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"API Error ({resp.status_code}): {resp.text}",
                    status_code=resp.status_code,
                )
            return resp.json()

    def stream_chat(self, path: str, json_data: dict[str, Any]):
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=60.0, follow_redirects=False) as client:
            with client.stream("POST", url, headers=self._get_headers(), json=json_data) as resp:
                for line in resp.iter_lines():
                    if line.startswith("data: "):
                        raw = line.removeprefix("data: ").strip()
                        if raw == "[DONE]":
                            break
                        try:
                            parsed = json.loads(raw)
                            delta = parsed.get("delta")
                            if delta:
                                yield delta
                        except Exception:
                            pass
