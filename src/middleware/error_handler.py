"""
src/middleware/error_handler.py

Converts LedgerError subclasses into the structured JSON error format
specified in Part A10.2.
"""
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from src.utils.exceptions import LedgerError


async def ledger_error_handler(request: Request, exc: LedgerError) -> JSONResponse:
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    body = {
        "error": {
            "type": exc.error_type,
            "code": exc.error_code,
            "message": str(exc),
            "details": {},
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }
    return JSONResponse(status_code=exc.http_status, content=body, headers={"X-Request-Id": request_id})
