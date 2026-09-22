import json
import os
import secrets
from pathlib import Path

from core.contracts.errors import ErrorCode, OximoronException

DEFAULT_CREDENTIAL_PATH = Path.home() / ".oximoron" / "run" / "credentials.json"
SERVICE_NAME = "oximoron_local_api"
KEY_NAME = "api_secret"

class SecretManager:
    def __init__(self, credential_path: Path | None = None):
        self.credential_path = credential_path or DEFAULT_CREDENTIAL_PATH
        self._current_token: str | None = None

    def get_or_create_token(self) -> str:
        if self._current_token:
            return self._current_token

        # 1. Try OS keyring
        try:
            import keyring
            token = keyring.get_password(SERVICE_NAME, KEY_NAME)
            if token:
                self._current_token = token
                return token
        except Exception:
            pass

        # 2. Try credential file if present and valid
        if self.credential_path.exists():
            try:
                with open(self.credential_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    token = data.get("api_token")
                    if token:
                        self._current_token = token
                        return token
            except Exception:
                pass

        # 3. Generate fresh token
        token = secrets.token_urlsafe(32)
        self._current_token = token

        # Store in keyring if possible
        try:
            import keyring
            keyring.set_password(SERVICE_NAME, KEY_NAME, token)
        except Exception:
            pass

        # Always save session credential file with 0600 permissions
        self.credential_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.credential_path.with_suffix(".tmp")
        try:
            fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"api_token": token}, f)
            os.replace(temp_path, str(self.credential_path))
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise OximoronException(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to write API credentials: {e}",
                status_code=500,
            )

        return token

    def validate_token(self, token_to_check: str) -> bool:
        current = self.get_or_create_token()
        return secrets.compare_digest(current, token_to_check)

    def cleanup(self) -> None:
        if self.credential_path.exists():
            try:
                self.credential_path.unlink()
            except Exception:
                pass
        self._current_token = None
