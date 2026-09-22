from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select

from apps.backend.dependencies import get_db_manager, verify_bearer_token
from core.contracts.errors import ErrorCode, OximoronException
from core.contracts.models import JobDescriptor
from core.jobs.manager import JobManager
from core.persistence.database import DatabaseManager
from core.persistence.models import JobModel

router = APIRouter(prefix="/jobs", tags=["Jobs"])

class JobListResponse(BaseModel):
    jobs: list[JobDescriptor]
    total: int

def get_job_manager(request) -> JobManager:
    return request.app.state.job_manager

@router.get("", response_model=JobListResponse)
async def list_jobs(
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    async with db.session() as session:
        stmt = select(JobModel).order_by(JobModel.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        items = result.scalars().all()

        count_stmt = select(JobModel)
        all_res = await session.execute(count_stmt)
        total = len(all_res.scalars().all())

        descriptors = [
            JobDescriptor(
                id=j.id,
                kind=j.kind,
                state=j.state,
                workspace_id=j.workspace_id,
                engine_id=j.engine_id,
                model_id=j.model_id,
                request_snapshot=j.request_snapshot,
                started_at=j.started_at,
                finished_at=j.finished_at,
                cancel_requested_at=j.cancel_requested_at,
                error_code=j.error_code,
                error_message=j.error_message,
                outcome=j.outcome_json,
                created_at=j.created_at,
            )
            for j in items
        ]
        return JobListResponse(jobs=descriptors, total=total)

@router.get("/{job_id}", response_model=JobDescriptor)
async def get_job_detail(
    job_id: str,
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
):
    async with db.session() as session:
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await session.execute(stmt)
        j = result.scalar_one_or_none()
        if not j:
            raise OximoronException(
                code=ErrorCode.NOT_FOUND,
                message=f"Job {job_id} not found",
                status_code=404,
            )

        return JobDescriptor(
            id=j.id,
            kind=j.kind,
            state=j.state,
            workspace_id=j.workspace_id,
            engine_id=j.engine_id,
            model_id=j.model_id,
            request_snapshot=j.request_snapshot,
            started_at=j.started_at,
            finished_at=j.finished_at,
            cancel_requested_at=j.cancel_requested_at,
            error_code=j.error_code,
            error_message=j.error_message,
            outcome=j.outcome_json,
            created_at=j.created_at,
        )

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
):
    # Retrieve JobManager from app state
    # or handle via JobModel update
    async with db.session() as session:
        stmt = select(JobModel).where(JobModel.id == job_id)
        res = await session.execute(stmt)
        j = res.scalar_one_or_none()
        if not j:
            raise OximoronException(
                code=ErrorCode.NOT_FOUND,
                message=f"Job {job_id} not found",
                status_code=404,
            )
        j.state = "cancelled"
    return {"status": "cancelled", "job_id": job_id}
