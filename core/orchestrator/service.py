import asyncio
from pathlib import Path

from sqlalchemy import select

from core.config.manager import ConfigManager
from core.contracts.enums import EngineState, JobKind, JobState
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    EngineDescriptor,
    JobDescriptor,
    gen_uuid,
    utc_now,
)
from core.events.broadcaster import EventBroadcaster
from core.jobs.manager import JobManager
from core.logging.logger import OximoronLogger
from core.persistence.database import DatabaseManager
from core.persistence.models import EngineModel
from core.process_manager.manager import ProcessManager
from engines.base.registry import AdapterRegistry

logger = OximoronLogger("orchestrator")

class Orchestrator:
    def __init__(
        self,
        db_manager: DatabaseManager,
        config_manager: ConfigManager,
        process_manager: ProcessManager,
        job_manager: JobManager,
        adapter_registry: AdapterRegistry,
        broadcaster: EventBroadcaster,
    ):
        self.db = db_manager
        self.config_mgr = config_manager
        self.process_mgr = process_manager
        self.jobs = job_manager
        self.adapters = adapter_registry
        self.broadcaster = broadcaster
        self._engine_locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, engine_id: str) -> asyncio.Lock:
        if engine_id not in self._engine_locks:
            self._engine_locks[engine_id] = asyncio.Lock()
        return self._engine_locks[engine_id]

    async def discover_candidates(self, roots: list[str] | None = None) -> list[EngineDescriptor]:
        search_roots = [Path(r) for r in (roots or [str(Path.home()), "/home/mevlec/Data"])]
        discovered: list[EngineDescriptor] = []

        for adapter in self.adapters.list_adapters():
            try:
                candidates = await adapter.detect(search_roots)
                discovered.extend(candidates)
            except Exception as e:
                logger.error(f"Discovery error in adapter {adapter.adapter_key}: {e}")

        return discovered

    async def register_engine(
        self,
        adapter_key: str,
        display_name: str,
        config_key: str,
    ) -> EngineDescriptor:
        adapter = self.adapters.get(adapter_key)
        cfg = self.config_mgr.config.engines.get(config_key)
        caps = await adapter.get_capabilities(cfg) if cfg else await adapter.get_capabilities(None)

        engine_id = gen_uuid()
        async with self.db.session() as session:
            model = EngineModel(
                id=engine_id,
                adapter_key=adapter_key,
                display_name=display_name,
                config_key=config_key,
                capability_json=caps.model_dump(mode="json"),
                observed_state=EngineState.CONFIGURED.value,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(model)

        return EngineDescriptor(
            id=engine_id,
            adapter_key=adapter_key,
            display_name=display_name,
            config_key=config_key,
            capabilities=caps,
            observed_state=EngineState.CONFIGURED,
        )

    async def list_engines(self) -> list[EngineDescriptor]:
        async with self.db.session() as session:
            stmt = select(EngineModel)
            res = await session.execute(stmt)
            models = res.scalars().all()

            descriptors = []
            for m in models:
                adapter = self.adapters.get(m.adapter_key)
                caps = await adapter.get_capabilities(self.config_mgr.config.engines.get(m.config_key))
                descriptors.append(
                    EngineDescriptor(
                        id=m.id,
                        adapter_key=m.adapter_key,
                        display_name=m.display_name,
                        config_key=m.config_key,
                        version=m.version,
                        capabilities=caps,
                        observed_state=EngineState(m.observed_state),
                        endpoint=m.endpoint,
                        last_health_at=m.last_health_at,
                    )
                )
            return descriptors

    async def start_engine(
        self,
        engine_id: str,
        model_path: str | None = None,
        model_id: str | None = None,
    ) -> JobDescriptor:
        lock = self._get_lock(engine_id)
        if lock.locked():
            raise OximoronException(
                code=ErrorCode.ENGINE_BUSY,
                message=f"Engine {engine_id} is already executing a lifecycle transition.",
                status_code=409,
            )

        async with self.db.session() as session:
            stmt = select(EngineModel).where(EngineModel.id == engine_id)
            res = await session.execute(stmt)
            engine = res.scalar_one_or_none()
            if not engine:
                raise OximoronException(
                    code=ErrorCode.ENGINE_NOT_CONFIGURED,
                    message=f"Engine {engine_id} is not registered.",
                    status_code=404,
                )

        job = await self.jobs.create_job(
            kind=JobKind.ENGINE_START,
            engine_id=engine_id,
            model_id=model_id,
            request_snapshot={"model_path": model_path},
        )

        asyncio.create_task(self._execute_start(job.id, engine_id, model_path, model_id))
        return job

    async def _execute_start(
        self,
        job_id: str,
        engine_id: str,
        model_path: str | None,
        model_id: str | None,
    ) -> None:
        async with self._get_lock(engine_id):
            try:
                await self.jobs.update_job_state(job_id, JobState.PREPARING)

                async with self.db.session() as session:
                    stmt = select(EngineModel).where(EngineModel.id == engine_id)
                    res = await session.execute(stmt)
                    engine = res.scalar_one()
                    adapter = self.adapters.get(engine.adapter_key)
                    engine_cfg = self.config_mgr.config.engines.get(engine.config_key)
                    if not engine_cfg:
                        raise OximoronException(
                            code=ErrorCode.ENGINE_NOT_CONFIGURED,
                            message=f"Missing configuration for engine key {engine.config_key}",
                            status_code=400,
                        )

                # Validate engine configuration
                is_valid, err = await adapter.validate(engine_cfg)
                if not is_valid:
                    raise OximoronException(
                        code=ErrorCode.ENGINE_START_FAILED,
                        message=f"Engine validation failed: {err}",
                        status_code=400,
                    )

                # Port allocation
                port = self.process_mgr.find_available_port(engine_cfg.preferred_port)

                # Build Launch Spec
                launch_spec = await adapter.build_launch_spec(engine_cfg, model_path, port)

                # Spawn
                proc_record = await self.process_mgr.spawn(engine_id, launch_spec, model_id=model_id)

                endpoint = f"http://127.0.0.1:{port}"
                async with self.db.session() as session:
                    stmt = select(EngineModel).where(EngineModel.id == engine_id)
                    res = await session.execute(stmt)
                    em = res.scalar_one()
                    em.observed_state = EngineState.STARTING.value
                    em.endpoint = endpoint

                await self.jobs.update_job_state(job_id, JobState.RUNNING)

                # Wait for health probe
                async def probe():
                    return await adapter.health_probe(endpoint)

                await self.process_mgr.wait_for_ready(
                    proc_record,
                    probe_fn=probe,
                    timeout_seconds=engine_cfg.startup_timeout_seconds,
                )

                async with self.db.session() as session:
                    stmt = select(EngineModel).where(EngineModel.id == engine_id)
                    res = await session.execute(stmt)
                    em = res.scalar_one()
                    em.observed_state = EngineState.READY.value
                    em.last_health_at = utc_now()

                await self.jobs.update_job_state(
                    job_id,
                    JobState.SUCCEEDED,
                    outcome={"endpoint": endpoint, "pid": proc_record.pid, "port": port},
                )
                logger.info(f"Engine {engine_id} successfully started on {endpoint}")

            except Exception as e:
                logger.error(f"Failed to start engine {engine_id}: {e}")
                err_code = getattr(e, "code", ErrorCode.ENGINE_START_FAILED)
                await self.jobs.update_job_state(
                    job_id,
                    JobState.FAILED,
                    error_code=err_code,
                    error_message=str(e),
                )
                async with self.db.session() as session:
                    stmt = select(EngineModel).where(EngineModel.id == engine_id)
                    res = await session.execute(stmt)
                    em = res.scalar_one_or_none()
                    if em:
                        em.observed_state = EngineState.FAILED.value

    async def stop_engine(self, engine_id: str) -> JobDescriptor:
        lock = self._get_lock(engine_id)
        if lock.locked():
            raise OximoronException(
                code=ErrorCode.ENGINE_BUSY,
                message=f"Engine {engine_id} is already in a transition.",
                status_code=409,
            )

        job = await self.jobs.create_job(kind=JobKind.ENGINE_STOP, engine_id=engine_id)
        asyncio.create_task(self._execute_stop(job.id, engine_id))
        return job

    async def _execute_stop(self, job_id: str, engine_id: str) -> None:
        async with self._get_lock(engine_id):
            try:
                await self.jobs.update_job_state(job_id, JobState.RUNNING)

                # Find active process for this engine
                from core.persistence.models import ProcessModel
                async with self.db.session() as session:
                    stmt = select(ProcessModel).where(
                        ProcessModel.engine_id == engine_id,
                        ProcessModel.status == "running"
                    )
                    res = await session.execute(stmt)
                    procs = res.scalars().all()

                for p in procs:
                    await self.process_mgr.stop(p.id)

                async with self.db.session() as session:
                    stmt = select(EngineModel).where(EngineModel.id == engine_id)
                    res = await session.execute(stmt)
                    em = res.scalar_one_or_none()
                    if em:
                        em.observed_state = EngineState.STOPPED.value
                        em.endpoint = None

                await self.jobs.update_job_state(job_id, JobState.SUCCEEDED)
            except Exception as e:
                logger.error(f"Error stopping engine {engine_id}: {e}")
                await self.jobs.update_job_state(
                    job_id,
                    JobState.FAILED,
                    error_code=ErrorCode.INTERNAL_ERROR,
                    error_message=str(e),
                )
