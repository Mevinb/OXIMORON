from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apps.backend.dependencies import get_hardware_service, verify_bearer_token
from core.contracts.models import GpuSnapshot, HardwareStatus, SystemSnapshot
from core.resource_manager.hardware import HardwareService

router = APIRouter(prefix="/system", tags=["System & Hardware"])

class GpuViewResponse(BaseModel):
    gpu_status: HardwareStatus
    gpus: list[GpuSnapshot]

@router.get("", response_model=SystemSnapshot)
async def get_system_snapshot(
    _token: str = Depends(verify_bearer_token),
    hw_service: HardwareService = Depends(get_hardware_service),
):
    return hw_service.get_snapshot()

@router.get("/gpu", response_model=GpuViewResponse)
async def get_gpu_snapshot(
    _token: str = Depends(verify_bearer_token),
    hw_service: HardwareService = Depends(get_hardware_service),
):
    snapshot = hw_service.get_snapshot()
    return GpuViewResponse(
        gpu_status=snapshot.gpu_status,
        gpus=snapshot.gpus,
    )
