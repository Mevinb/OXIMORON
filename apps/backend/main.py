import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apps.backend.api.v1.chat import router as chat_router
from apps.backend.api.v1.conversations import router as conversations_router
from apps.backend.api.v1.engines import router as engines_router
from apps.backend.api.v1.events import router as events_router
from apps.backend.api.v1.generations import router as generations_router
from apps.backend.api.v1.health import router as health_router
from apps.backend.api.v1.jobs import router as jobs_router
from apps.backend.api.v1.logs import router as logs_router
from apps.backend.api.v1.models import router as models_router
from apps.backend.api.v1.settings import router as settings_router
from apps.backend.api.v1.system import router as system_router
from apps.backend.lifespan import lifespan
from apps.backend.middleware import SecurityAndTracingMiddleware
from core.config.manager import ConfigManager
from core.contracts.errors import (
    APIErrorResponse,
    ErrorCode,
    ErrorDetail,
    OximoronException,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="OXIMORON API",
        version="0.1.0",
        description="Local-first desktop AI orchestration platform",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Security & Tracing Middleware
    app.add_middleware(SecurityAndTracingMiddleware)

    # Exception Handlers
    @app.exception_handler(OximoronException)
    async def oximoron_exception_handler(request: Request, exc: OximoronException):
        request_id = getattr(request.state, "request_id", None)
        error_resp = APIErrorResponse(error=exc.to_error_detail(request_id=request_id))
        return JSONResponse(
            status_code=exc.status_code,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        error_resp = APIErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.INVALID_CONFIG,
                message=f"Validation failed: {exc.errors()}",
                request_id=request_id,
                details={"errors": str(exc.errors())},
            )
        )
        return JSONResponse(
            status_code=422,
            content=error_resp.model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        error_resp = APIErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Internal server error: {exc}",
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=500,
            content=error_resp.model_dump(),
        )

    # Include all API Routers under /api/v1
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(logs_router, prefix="/api/v1")
    app.include_router(settings_router, prefix="/api/v1")
    app.include_router(engines_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(generations_router, prefix="/api/v1")

    return app

def run_server():
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.load()
    host = cfg.server.host
    port = cfg.server.preferred_port

    print(f"Starting OXIMORON on {host}:{port}...")
    uvicorn.run(
        "apps.backend.main:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    run_server()
