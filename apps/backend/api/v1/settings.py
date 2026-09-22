from fastapi import APIRouter, Depends, Query

from apps.backend.dependencies import get_config_manager, verify_bearer_token
from core.config.manager import ConfigManager
from core.config.models import AppConfig

router = APIRouter(prefix="/settings", tags=["Settings & Configuration"])

@router.get("", response_model=AppConfig)
async def get_settings(
    _token: str = Depends(verify_bearer_token),
    config_mgr: ConfigManager = Depends(get_config_manager),
):
    return config_mgr.config

@router.put("", response_model=AppConfig)
async def update_settings(
    updated_config: AppConfig,
    _token: str = Depends(verify_bearer_token),
    expected_revision: int | None = Query(default=None),
    config_mgr: ConfigManager = Depends(get_config_manager),
):
    saved = config_mgr.save(updated_config, expected_revision=expected_revision)
    return saved
