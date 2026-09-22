from pathlib import Path

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from apps.backend.dependencies import get_config_manager, get_db_manager, verify_bearer_token
from core.config.manager import ConfigManager
from core.contracts.enums import ModelFormat, ModelRole
from core.contracts.models import ModelDescriptor
from core.model_registry.scanner import ModelScanner
from core.model_registry.service import ModelService
from core.persistence.database import DatabaseManager

router = APIRouter(prefix="/models", tags=["Models"])

class ScanRequest(BaseModel):
    roots: list[str] | None = None
    depth_limit: int = 4

class ScanResponse(BaseModel):
    status: str
    discovered_count: int

@router.get("", response_model=list[ModelDescriptor])
async def list_models(
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
    role: ModelRole | None = Query(default=None),
    format: ModelFormat | None = Query(default=None),
    search: str | None = Query(default=None),
):
    service = ModelService(db)
    return await service.list_models(role=role, format=format, search=search)

@router.post("/scan", response_model=ScanResponse)
async def scan_models(
    req: ScanRequest = ScanRequest(),
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
    config_mgr: ConfigManager = Depends(get_config_manager),
):
    scanner = ModelScanner(db)
    roots_to_scan = [Path(r) for r in req.roots] if req.roots else [
        Path(p) for p in config_mgr.config.storage.scan_roots
    ]
    if not roots_to_scan:
        # Default scan roots
        roots_to_scan = [
            Path("/home/mevlec/Data/forge/stable-diffusion-webui-forge/models"),
            Path("/home/mevlec/llama.cpp/models"),
        ]

    count = await scanner.scan_roots(roots_to_scan, depth_limit=req.depth_limit)
    return ScanResponse(status="completed", discovered_count=count)

@router.get("/{model_id}", response_model=ModelDescriptor)
async def get_model(
    model_id: str,
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
):
    service = ModelService(db)
    return await service.get_model(model_id)

@router.patch("/{model_id}", response_model=ModelDescriptor)
async def update_model(
    model_id: str,
    _token: str = Depends(verify_bearer_token),
    db: DatabaseManager = Depends(get_db_manager),
):
    service = ModelService(db)
    return await service.toggle_favorite(model_id)
