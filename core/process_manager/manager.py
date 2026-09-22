import asyncio
import os
import signal
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import psutil
from sqlalchemy import select

from core.contracts.enums import ProcessStatus
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import LaunchSpec, ProcessRecord, gen_uuid, utc_now
from core.logging.logger import OximoronLogger, redact_text
from core.persistence.database import DatabaseManager
from core.persistence.models import ProcessModel

logger = OximoronLogger("process_manager")

class ProcessManager:
    def __init__(self, db_manager: DatabaseManager, log_dir: Path | None = None):
        self.db = db_manager
        self.log_dir = log_dir or (Path.home() / ".oximoron" / "logs" / "engines")
        self._active_processes: dict[str, subprocess.Popen] = {}
        self._lock = asyncio.Lock()

    def is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True

    def find_available_port(self, start_port: int, max_tries: int = 10, host: str = "127.0.0.1") -> int:
        for p in range(start_port, start_port + max_tries):
            if not self.is_port_in_use(p, host):
                return p
        raise OximoronException(
            code=ErrorCode.PORT_CONFLICT,
            message=f"No available ports found in range {start_port} - {start_port + max_tries}",
            status_code=409,
        )

    async def spawn(
        self,
        engine_id: str,
        launch_spec: LaunchSpec,
        model_id: str | None = None,
    ) -> ProcessRecord:
        # Validate executable
        exe_path = Path(launch_spec.executable)
        if not exe_path.exists() or not os.access(str(exe_path), os.X_OK):
            raise OximoronException(
                code=ErrorCode.ENGINE_START_FAILED,
                message=f"Executable does not exist or is not executable: {launch_spec.executable}",
                status_code=400,
            )

        cmd = [launch_spec.executable] + launch_spec.arguments
        cmd_fingerprint = f"{launch_spec.executable} {' '.join(launch_spec.arguments)}"[:120]

        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = self.log_dir / f"{engine_id}_{int(datetime.now(timezone.utc).timestamp())}.log"

        # Sanitize environment
        clean_env = os.environ.copy()
        clean_env.update(launch_spec.environment)

        # Spawn in a new process group on Linux to ensure all descendants are tracked
        def preexec():
            os.setpgid(0, 0)

        log_file = open(log_file_path, "w", encoding="utf-8")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=launch_spec.working_directory,
                env=clean_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=preexec,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            log_file.close()
            raise OximoronException(
                code=ErrorCode.ENGINE_START_FAILED,
                message=f"Failed to spawn process: {e}",
                status_code=500,
            )

        ps_proc = psutil.Process(proc.pid)
        create_time = ps_proc.create_time()
        group_id = os.getpgid(proc.pid)
        record_id = gen_uuid()

        record = ProcessRecord(
            id=record_id,
            engine_id=engine_id,
            pid=proc.pid,
            create_time=create_time,
            command_fingerprint=cmd_fingerprint,
            group_id=group_id,
            port=launch_spec.port,
            model_id=model_id,
            status=ProcessStatus.RUNNING,
            log_path=str(log_file_path),
        )

        async with self._lock:
            self._active_processes[record_id] = proc

        # Async background reader for logs
        asyncio.create_task(self._stream_logs(record_id, proc, log_file))

        # Save to database
        async with self.db.session() as session:
            model = ProcessModel(
                id=record.id,
                engine_id=record.engine_id,
                pid=record.pid,
                create_time=record.create_time,
                executable_identity=launch_spec.executable,
                command_fingerprint=cmd_fingerprint,
                group_id=group_id,
                port=record.port,
                model_id=model_id,
                status=ProcessStatus.RUNNING.value,
                log_ref=str(log_file_path),
                start_at=utc_now(),
            )
            session.add(model)

        logger.info(f"Spawned engine process {proc.pid} for engine {engine_id} on port {launch_spec.port}")
        return record

    async def _stream_logs(self, record_id: str, proc: subprocess.Popen, log_file) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                line = await loop.run_in_executor(None, proc.stdout.readline)
                if not line:
                    break
                clean_line = redact_text(line)
                log_file.write(clean_line)
                log_file.flush()
        except Exception:
            pass
        finally:
            log_file.close()

    async def wait_for_ready(
        self,
        record: ProcessRecord,
        probe_fn: Callable[[], Any],
        timeout_seconds: int = 60,
    ) -> bool:
        start_time = asyncio.get_event_loop().time()
        delay = 0.25

        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            # Check if process died
            proc = self._active_processes.get(record.id)
            if proc and proc.poll() is not None:
                raise OximoronException(
                    code=ErrorCode.ENGINE_START_FAILED,
                    message=f"Process exited prematurely with code {proc.returncode}",
                    status_code=500,
                )

            # Probe readiness
            try:
                is_ready, details = await probe_fn()
                if is_ready:
                    logger.info(f"Engine {record.engine_id} on port {record.port} is READY")
                    return True
            except Exception:
                pass

            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 2.0)

        # Timeout reached, stop process
        await self.stop(record.id)
        raise OximoronException(
            code=ErrorCode.ENGINE_NOT_READY,
            message=f"Engine failed to become ready within {timeout_seconds} seconds",
            status_code=504,
        )

    async def stop(self, record_id: str, graceful_timeout: int = 10) -> bool:
        async with self._lock:
            self._active_processes.pop(record_id, None)

        async with self.db.session() as session:
            stmt = select(ProcessModel).where(ProcessModel.id == record_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if not model:
                return False

            pid = model.pid
            create_time = model.create_time
            group_id = model.group_id

        # Verify identity before sending signals to prevent killing reused PIDs
        try:
            ps_proc = psutil.Process(pid)
            if abs(ps_proc.create_time() - create_time) > 2.0:
                logger.warning(f"PID {pid} create time mismatch. Skipping kill to prevent killing unrelated process.")
                return False
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            logger.info(f"Process {pid} already dead.")
            return True

        # Send SIGTERM to process group
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            return True
        except Exception as e:
            logger.error(f"Failed to send SIGTERM to process group {group_id}: {e}")

        # Wait for graceful exit
        deadline = asyncio.get_event_loop().time() + graceful_timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                ps_proc = psutil.Process(pid)
                if not ps_proc.is_running():
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            await asyncio.sleep(0.5)

        # Escalate to SIGKILL if still running
        try:
            ps_proc = psutil.Process(pid)
            if ps_proc.is_running():
                logger.warning(f"Process {pid} did not exit after {graceful_timeout}s. Sending SIGKILL to process group {group_id}.")
                os.killpg(group_id, signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
            pass

        # Update DB status
        async with self.db.session() as session:
            stmt = select(ProcessModel).where(ProcessModel.id == record_id)
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if model:
                model.status = ProcessStatus.STOPPED.value
                model.exit_at = utc_now()

        logger.info(f"Stopped process group {group_id} (pid {pid})")
        return True

    async def reconcile_stale_processes(self) -> int:
        reconciled = 0
        async with self.db.session() as session:
            stmt = select(ProcessModel).where(ProcessModel.status == ProcessStatus.RUNNING.value)
            res = await session.execute(stmt)
            running_models = res.scalars().all()

            for pm in running_models:
                is_alive = False
                try:
                    p = psutil.Process(pm.pid)
                    if p.is_running() and abs(p.create_time() - pm.create_time) < 2.0:
                        is_alive = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                if not is_alive:
                    pm.status = ProcessStatus.RECONCILED_DEAD.value
                    pm.exit_at = utc_now()
                    reconciled += 1

        if reconciled > 0:
            logger.info(f"Reconciled {reconciled} dead process records on startup.")
        return reconciled
