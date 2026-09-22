from fastapi import Header, Request

from core.config.manager import ConfigManager
from core.contracts.errors import ErrorCode, OximoronException
from core.events.broadcaster import EventBroadcaster
from core.persistence.database import DatabaseManager
from core.resource_manager.hardware import HardwareService
from core.secrets.manager import SecretManager


def get_config_manager(request: Request) -> ConfigManager:
    return request.app.state.config_manager

def get_db_manager(request: Request) -> DatabaseManager:
    return request.app.state.db_manager

def get_secret_manager(request: Request) -> SecretManager:
    return request.app.state.secret_manager

def get_event_broadcaster(request: Request) -> EventBroadcaster:
    return request.app.state.event_broadcaster

def get_hardware_service(request: Request) -> HardwareService:
    return request.app.state.hardware_service

def verify_bearer_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str:
    secret_manager: SecretManager = request.app.state.secret_manager
    if not authorization or not authorization.startswith("Bearer "):
        raise OximoronException(
            code=ErrorCode.UNAUTHORIZED,
            message="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
            status_code=401,
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not secret_manager.validate_token(token):
        raise OximoronException(
            code=ErrorCode.UNAUTHORIZED,
            message="Invalid or expired API token.",
            status_code=401,
        )
    return token
