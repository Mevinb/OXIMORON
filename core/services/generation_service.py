import base64
import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from core.contracts.enums import JobKind, JobState
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import (
    ArtifactDescriptor,
    GenerationDescriptor,
    ImageGenerationRequest,
    gen_uuid,
    utc_now,
)
from core.jobs.manager import JobManager
from core.logging.logger import OximoronLogger
from core.persistence.database import DatabaseManager
from core.persistence.models import ArtifactModel, EngineModel, GenerationModel
from engines.base.registry import AdapterRegistry

logger = OximoronLogger("generation_service")

class GenerationService:
    def __init__(
        self,
        db_manager: DatabaseManager,
        job_manager: JobManager,
        adapter_registry: AdapterRegistry,
        artifact_dir: Path | None = None,
    ):
        self.db = db_manager
        self.jobs = job_manager
        self.adapters = adapter_registry
        self.artifact_dir = artifact_dir or (Path.home() / "OXIMORON" / "generations")

    async def generate_image(self, request: ImageGenerationRequest) -> GenerationDescriptor:
        # 1. Create Job
        job = await self.jobs.create_job(
            kind=JobKind.IMAGE_GENERATION,
            engine_id=request.engine_id,
            model_id=request.model_id,
            request_snapshot=request.model_dump(),
        )
        cancel_event = self.jobs.get_cancel_event(job.id)

        # 2. Resolve Forge endpoint
        endpoint = "http://127.0.0.1:7860"
        if request.engine_id:
            async with self.db.session() as session:
                stmt = select(EngineModel).where(EngineModel.id == request.engine_id)
                res = await session.execute(stmt)
                eng = res.scalar_one_or_none()
                if eng and eng.endpoint:
                    endpoint = eng.endpoint

        adapter = self.adapters.get("forge")
        await self.jobs.update_job_state(job.id, JobState.RUNNING)

        try:
            start_t = datetime.now(timezone.utc)
            gen_result = await adapter.generate_image(endpoint, request, cancel_event=cancel_event)

            if gen_result.get("status") == "cancelled":
                await self.jobs.update_job_state(job.id, JobState.CANCELLED)
                raise OximoronException(code=ErrorCode.INTERNAL_ERROR, message="Generation cancelled", status_code=499)

            duration_ms = int((datetime.now(timezone.utc) - start_t).total_seconds() * 1000)
            images_b64 = gen_result.get("images", [])

            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            artifacts: list[ArtifactDescriptor] = []
            gen_id = gen_uuid()

            for idx, img_data in enumerate(images_b64):
                # Decode base64
                if "," in img_data:
                    img_data = img_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(img_data)
                byte_size = len(raw_bytes)
                sha256 = hashlib.sha256(raw_bytes).hexdigest()

                # Atomic write
                art_id = gen_uuid()
                filename = f"gen_{gen_id[:8]}_{idx}_{sha256[:8]}.png"
                target_path = self.artifact_dir / filename

                temp_fd, temp_file = tempfile.mkstemp(
                    dir=str(self.artifact_dir),
                    prefix="art_",
                    suffix=".tmp",
                )
                with os.fdopen(temp_fd, "wb") as f:
                    f.write(raw_bytes)
                os.replace(temp_file, str(target_path))

                art = ArtifactDescriptor(
                    id=art_id,
                    generation_id=gen_id,
                    kind="image",
                    relative_path=filename,
                    absolute_path=str(target_path),
                    media_type="image/png",
                    byte_size=byte_size,
                    hash=sha256,
                    width=request.width,
                    height=request.height,
                )
                artifacts.append(art)

            # Persist Generation & Artifacts in DB
            effective_seed = gen_result.get("seed", request.seed)
            async with self.db.session() as session:
                gen_entity = GenerationModel(
                    id=gen_id,
                    job_id=job.id,
                    workspace_id="default",
                    engine_id=request.engine_id or "forge",
                    model_id=request.model_id,
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    requested_settings_json=request.model_dump(),
                    effective_settings_json=gen_result.get("parameters", {}),
                    seed=effective_seed,
                    duration_ms=duration_ms,
                    status="completed",
                    created_at=utc_now(),
                )
                session.add(gen_entity)

                for a in artifacts:
                    am = ArtifactModel(
                        id=a.id,
                        generation_id=gen_id,
                        kind="image",
                        relative_path=a.relative_path,
                        absolute_path=a.absolute_path,
                        media_type=a.media_type,
                        byte_size=a.byte_size,
                        hash=a.hash,
                        width=a.width,
                        height=a.height,
                        created_at=utc_now(),
                    )
                    session.add(am)

            await self.jobs.update_job_state(
                job.id,
                JobState.SUCCEEDED,
                outcome={"generation_id": gen_id, "artifacts_count": len(artifacts)},
            )

            return GenerationDescriptor(
                id=gen_id,
                job_id=job.id,
                workspace_id="default",
                engine_id=request.engine_id or "forge",
                model_id=request.model_id,
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                requested_settings=request.model_dump(),
                effective_settings=gen_result.get("parameters", {}),
                seed=effective_seed,
                duration_ms=duration_ms,
                status="completed",
                artifacts=artifacts,
            )

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            await self.jobs.update_job_state(
                job.id,
                JobState.FAILED,
                error_code=ErrorCode.INTERNAL_ERROR,
                error_message=str(e),
            )
            raise

    async def list_generations(self, limit: int = 50) -> list[GenerationDescriptor]:
        async with self.db.session() as session:
            stmt = select(GenerationModel).order_by(GenerationModel.created_at.desc()).limit(limit)
            res = await session.execute(stmt)
            gens = res.scalars().all()

            descriptors = []
            for g in gens:
                art_stmt = select(ArtifactModel).where(ArtifactModel.generation_id == g.id)
                art_res = await session.execute(art_stmt)
                arts = [
                    ArtifactDescriptor(
                        id=a.id,
                        generation_id=a.generation_id,
                        kind=a.kind,
                        relative_path=a.relative_path,
                        absolute_path=a.absolute_path,
                        media_type=a.media_type,
                        byte_size=a.byte_size,
                        hash=a.hash,
                        width=a.width,
                        height=a.height,
                    )
                    for a in art_res.scalars().all()
                ]

                descriptors.append(
                    GenerationDescriptor(
                        id=g.id,
                        job_id=g.job_id,
                        workspace_id=g.workspace_id,
                        engine_id=g.engine_id,
                        model_id=g.model_id,
                        prompt=g.prompt,
                        negative_prompt=g.negative_prompt,
                        requested_settings=g.requested_settings_json or {},
                        effective_settings=g.effective_settings_json or {},
                        seed=g.seed,
                        duration_ms=g.duration_ms,
                        status=g.status,
                        artifacts=arts,
                        created_at=g.created_at,
                    )
                )
            return descriptors

    async def get_artifact(self, artifact_id: str) -> ArtifactDescriptor:
        async with self.db.session() as session:
            stmt = select(ArtifactModel).where(ArtifactModel.id == artifact_id)
            res = await session.execute(stmt)
            a = res.scalar_one_or_none()
            if not a:
                raise OximoronException(code=ErrorCode.NOT_FOUND, message=f"Artifact {artifact_id} not found", status_code=404)

            return ArtifactDescriptor(
                id=a.id,
                generation_id=a.generation_id,
                kind=a.kind,
                relative_path=a.relative_path,
                absolute_path=a.absolute_path,
                media_type=a.media_type,
                byte_size=a.byte_size,
                hash=a.hash,
                width=a.width,
                height=a.height,
            )
