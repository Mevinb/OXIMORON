import re

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from core.contracts.errors import APIErrorResponse, ErrorCode, ErrorDetail
from core.contracts.models import gen_uuid

ALLOWED_ORIGIN_PATTERNS = [
    re.compile(r"^https?://localhost(:\d+)?$"),
    re.compile(r"^https?://127\.0\.0\.1(:\d+)?$"),
    re.compile(r"^tauri://localhost$"),
    re.compile(r"^http://tauri\.localhost$"),
]

class SecurityAndTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Request ID
        request_id = request.headers.get("x-request-id") or gen_uuid()
        request.state.request_id = request_id

        # 2. Host validation
        host = request.headers.get("host", "")
        host_name = host.split(":")[0].lower()
        if host_name not in ["127.0.0.1", "localhost", "0.0.0.0", "testserver"]:
            error_resp = APIErrorResponse(
                error=ErrorDetail(
                    code=ErrorCode.FORBIDDEN_ORIGIN,
                    message=f"Invalid Host header '{host}'. Loopback binding only.",
                    request_id=request_id,
                )
            )
            return JSONResponse(
                status_code=403,
                content=error_resp.model_dump(),
            )

        # 3. Origin validation
        origin = request.headers.get("origin")
        if origin:
            is_allowed = any(p.match(origin) for p in ALLOWED_ORIGIN_PATTERNS)
            if not is_allowed:
                error_resp = APIErrorResponse(
                    error=ErrorDetail(
                        code=ErrorCode.FORBIDDEN_ORIGIN,
                        message=f"Cross-Origin request from origin '{origin}' is forbidden.",
                        request_id=request_id,
                    )
                )
                return JSONResponse(
                    status_code=403,
                    content=error_resp.model_dump(),
                )

        if request.method == "OPTIONS":
            resp = Response(status_code=204)
            resp.headers["X-Request-ID"] = request_id
            if origin and any(p.match(origin) for p in ALLOWED_ORIGIN_PATTERNS):
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Credentials"] = "true"
                resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Idempotency-Key, X-Request-ID"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            return resp

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        if origin and any(p.match(origin) for p in ALLOWED_ORIGIN_PATTERNS):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Idempotency-Key, X-Request-ID"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"

        return response
