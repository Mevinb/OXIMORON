import fcntl
import json
import os
from pathlib import Path

import psutil

from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import RuntimeDiscoveryRecord

DEFAULT_LOCK_PATH = Path.home() / ".oximoron" / "run" / ".supervisor.lock"
DEFAULT_DISCOVERY_PATH = Path.home() / ".oximoron" / "run" / "discovery.json"

class SupervisorLock:
    def __init__(
        self,
        lock_path: Path | None = None,
        discovery_path: Path | None = None,
    ):
        self.lock_path = lock_path or DEFAULT_LOCK_PATH
        self.discovery_path = discovery_path or DEFAULT_DISCOVERY_PATH
        self._lock_file = None
        self._is_locked = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_file = open(self.lock_path, "a+")

        try:
            fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._is_locked = True
        except (BlockingIOError, OSError):
            # Another process holds the lock
            existing_discovery = self.read_discovery()
            if existing_discovery:
                # Check if existing process is actually alive
                try:
                    proc = psutil.Process(existing_discovery.pid)
                    if proc.is_running() and abs(proc.create_time() - existing_discovery.create_time) < 2.0:
                        raise OximoronException(
                            code=ErrorCode.CONFLICT,
                            message=f"Another supervisor instance {existing_discovery.supervisor_instance_id} is running on pid {existing_discovery.pid} ({existing_discovery.base_url})",
                            status_code=409,
                            details={"instance_id": existing_discovery.supervisor_instance_id, "pid": existing_discovery.pid, "url": existing_discovery.base_url},
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            raise OximoronException(
                code=ErrorCode.CONFLICT,
                message="Cannot acquire supervisor lock: another backend process is currently starting or running.",
                status_code=409,
            )

    def write_discovery(self, record: RuntimeDiscoveryRecord) -> None:
        if not self._is_locked:
            raise RuntimeError("Cannot write discovery record without holding supervisor lock.")
        
        temp_path = self.discovery_path.with_suffix(".tmp")
        fd = os.open(str(temp_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record.model_dump(mode="json"), f, indent=2)
        os.replace(temp_path, str(self.discovery_path))

    def read_discovery(self) -> RuntimeDiscoveryRecord | None:
        if not self.discovery_path.exists():
            return None
        try:
            with open(self.discovery_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return RuntimeDiscoveryRecord.model_validate(data)
        except Exception:
            return None

    def release(self) -> None:
        if self.discovery_path.exists():
            try:
                self.discovery_path.unlink()
            except Exception:
                pass

        if self._lock_file and self._is_locked:
            try:
                fcntl.flock(self._lock_file.fileno(), fcntl.LOCK_UN)
                self._lock_file.close()
            except Exception:
                pass
            self._is_locked = False
            self._lock_file = None
