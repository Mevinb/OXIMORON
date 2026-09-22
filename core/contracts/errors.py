from typing import Any

from pydantic import BaseModel, Field


class ErrorCode:
    ENGINE_NOT_CONFIGURED = "ENGINE_NOT_CONFIGURED"
    ENGINE_UNSUPPORTED = "ENGINE_UNSUPPORTED"
    ENGINE_START_FAILED = "ENGINE_START_FAILED"
    ENGINE_NOT_READY = "ENGINE_NOT_READY"
    ENGINE_BUSY = "ENGINE_BUSY"
    PROCESS_IDENTITY_MISMATCH = "PROCESS_IDENTITY_MISMATCH"
    PORT_CONFLICT = "PORT_CONFLICT"
    MODEL_MISSING = "MODEL_MISSING"
    MODEL_INCOMPATIBLE = "MODEL_INCOMPATIBLE"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    GPU_METRICS_UNAVAILABLE = "GPU_METRICS_UNAVAILABLE"
    OFFLINE_POLICY = "OFFLINE_POLICY"
    KEYRING_UNAVAILABLE = "KEYRING_UNAVAILABLE"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PERMISSION_REQUIRED = "PERMISSION_REQUIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_CONFIG = "INVALID_CONFIG"
    DISK_FULL = "DISK_FULL"
    CANCEL_UNSUPPORTED = "CANCEL_UNSUPPORTED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    EVENT_CURSOR_EXPIRED = "EVENT_CURSOR_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN_ORIGIN = "FORBIDDEN_ORIGIN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    retryable: bool = False
    action: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

class APIErrorResponse(BaseModel):
    error: ErrorDetail

class OximoronException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        retryable: bool = False,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable
        self.action = action
        self.details = details or {}

    def to_error_detail(self, request_id: str | None = None) -> ErrorDetail:
        return ErrorDetail(
            code=self.code,
            message=self.message,
            request_id=request_id,
            retryable=self.retryable,
            action=self.action,
            details=self.details,
        )
