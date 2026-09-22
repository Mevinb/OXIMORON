from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from apps.backend.dependencies import verify_bearer_token
from core.contracts.models import EngineDescriptor, JobDescriptor
from core.orchestrator.service import Orchestrator

router = APIRouter(prefix="/engines", tags=["Engines"])

class RegisterEngineRequest(BaseModel):
    adapter_key: str
    display_name: str
    config_key: str

class StartEngineRequest(BaseModel):
    model_path: str | None = None
    model_id: str | None = None

def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

@router.get("", response_model=list[EngineDescriptor])
async def list_engines(
    _token: str = Depends(verify_bearer_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return await orchestrator.list_engines()

@router.post("", response_model=EngineDescriptor)
async def register_engine(
    req: RegisterEngineRequest,
    _token: str = Depends(verify_bearer_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return await orchestrator.register_engine(
        adapter_key=req.adapter_key,
        display_name=req.display_name,
        config_key=req.config_key,
    )

@router.post("/discover", response_model=list[EngineDescriptor])
async def discover_engines(
    _token: str = Depends(verify_bearer_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return await orchestrator.discover_candidates()

@router.post("/{engine_id}/start", response_model=JobDescriptor)
async def start_engine(
    engine_id: str,
    req: StartEngineRequest = StartEngineRequest(),
    _token: str = Depends(verify_bearer_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return await orchestrator.start_engine(
        engine_id=engine_id,
        model_path=req.model_path,
        model_id=req.model_id,
    )

@router.post("/{engine_id}/stop", response_model=JobDescriptor)
async def stop_engine(
    engine_id: str,
    _token: str = Depends(verify_bearer_token),
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return await orchestrator.stop_engine(engine_id=engine_id)
