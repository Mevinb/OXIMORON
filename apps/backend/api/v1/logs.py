from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps.backend.dependencies import verify_bearer_token
from core.logging.logger import LogEntry, memory_log_buffer

router = APIRouter(prefix="/logs", tags=["Logs & Diagnostics"])

class LogsResponse(BaseModel):
    entries: list[LogEntry]
    total_count: int

@router.get("", response_model=LogsResponse)
async def get_logs(
    _token: str = Depends(verify_bearer_token),
    level: str | None = Query(default=None, description="Filter by log level (INFO, WARNING, ERROR, DEBUG)"),
    component: str | None = Query(default=None, description="Filter by component name"),
    limit: int = Query(default=100, ge=1, le=1000),
    before_id: str | None = Query(default=None),
):
    entries = memory_log_buffer.query(
        level=level,
        component=component,
        limit=limit,
        before_id=before_id,
    )
    return LogsResponse(
        entries=entries,
        total_count=len(entries),
    )
