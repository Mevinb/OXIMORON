from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from apps.backend.dependencies import (
    get_hardware_service,
    verify_bearer_token,
)
from core.contracts.models import HardwareStatus, utc_now
from core.resource_manager.hardware import HardwareService

router = APIRouter(tags=["Health & Status"])

class SubsystemStatus(BaseModel):
    database: str = "ok"
    hardware_nvml: HardwareStatus
    supervisor: str = "ok"

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    protocol_version: str = "1.0.0"
    subsystems: SubsystemStatus
    timestamp: str = Field(default_factory=lambda: utc_now().isoformat())

class StatusSummary(BaseModel):
    status: str = "ok"
    supervisor_id: str
    active_engines: int = 0
    active_jobs: int = 0
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_available: bool

class SessionResponse(BaseModel):
    token: str
    supervisor_id: str

@router.get("/health", response_model=HealthResponse)
async def get_health(
    request: Request,
    hw_service: HardwareService = Depends(get_hardware_service),
):
    snapshot = hw_service.get_snapshot()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        protocol_version="1.0.0",
        subsystems=SubsystemStatus(
            database="ok",
            hardware_nvml=snapshot.gpu_status,
            supervisor="ok",
        ),
    )

@router.get("/session", response_model=SessionResponse)
async def get_session(
    request: Request,
):
    token = getattr(request.app.state, "api_token", "")
    discovery = getattr(request.app.state, "discovery_record", None)
    sup_id = discovery.supervisor_instance_id if discovery else "unknown"
    return SessionResponse(
        token=token,
        supervisor_id=sup_id,
    )

@router.get("/status", response_model=StatusSummary)
async def get_status(
    request: Request,
    _token: str = Depends(verify_bearer_token),
    hw_service: HardwareService = Depends(get_hardware_service),
):
    snapshot = hw_service.get_snapshot()
    discovery = getattr(request.app.state, "discovery_record", None)
    sup_id = discovery.supervisor_instance_id if discovery else "unknown"

    return StatusSummary(
        status="ok",
        supervisor_id=sup_id,
        active_engines=0,
        active_jobs=0,
        cpu_percent=snapshot.cpu_utilization_pct,
        ram_used_gb=round(snapshot.ram_used_bytes / 1e9, 2),
        ram_total_gb=round(snapshot.ram_total_bytes / 1e9, 2),
        gpu_available=snapshot.gpu_status.available,
    )
