import os
import tempfile
from pathlib import Path

import yaml

from core.config.models import AppConfig
from core.contracts.errors import ErrorCode, OximoronException

DEFAULT_CONFIG_PATH = Path.home() / ".oximoron" / "config.yaml"

class ConfigManager:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._config: AppConfig | None = None

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self.load()
        return self._config

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            default_cfg = AppConfig()
            self.save(default_cfg)
            self._config = default_cfg
            return self._config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f) or {}
            self._config = AppConfig.model_validate(raw_data)
            return self._config
        except Exception as e:
            # Preserve prior config if available in memory
            raise OximoronException(
                code=ErrorCode.INVALID_CONFIG,
                message=f"Failed to load configuration from {self.config_path}: {e}",
                status_code=500,
                details={"path": str(self.config_path), "raw_error": str(e)},
            )

    def save(self, new_config: AppConfig, expected_revision: int | None = None) -> AppConfig:
        if expected_revision is not None and self._config is not None:
            if self._config.revision != expected_revision:
                raise OximoronException(
                    code=ErrorCode.CONFLICT,
                    message=f"Config revision conflict: expected {expected_revision}, current is {self._config.revision}",
                    status_code=409,
                    details={"current_revision": self._config.revision, "expected_revision": expected_revision},
                )

        new_config.revision = (self._config.revision + 1) if self._config else 1
        data_dict = new_config.model_dump(mode="json")

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write via temporary file
        temp_fd, temp_file = tempfile.mkstemp(
            dir=str(self.config_path.parent),
            prefix="config_",
            suffix=".tmp"
        )
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                yaml.dump(data_dict, f, default_flow_style=False, sort_keys=False)
            os.replace(temp_file, str(self.config_path))
            self._config = new_config
            return self._config
        except Exception as e:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise OximoronException(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to write config atomically: {e}",
                status_code=500,
                details={"path": str(self.config_path), "raw_error": str(e)},
            )
