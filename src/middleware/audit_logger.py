"""
src/middleware/audit_logger.py

Structured request/response logging (Part A10.3) using structlog.
Every request gets a unique request_id returned in the response header,
enabling end-to-end tracing through logs.
"""
import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger("ledger.audit")


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-Id"] = request_id

        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
