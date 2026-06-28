"""
src/main.py — FastAPI application entrypoint.
"""
from fastapi import FastAPI
from src.config.settings import settings
from src.middleware.error_handler import ledger_error_handler
from src.middleware.audit_logger import AuditLoggingMiddleware
from src.utils.exceptions import LedgerError
from src.routes import transactions, reports, audit
from src.jobs.scheduler import create_scheduler

app = FastAPI(
    title="Ledger System API",
    description="Double-Entry Accounting & Immutable Audit Trail",
    version="0.1.0",
)

_scheduler = create_scheduler()


@app.on_event("startup")
def start_scheduler():
    _scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    _scheduler.shutdown(wait=False)

app.add_middleware(AuditLoggingMiddleware)
app.add_exception_handler(LedgerError, ledger_error_handler)

app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(audit.router)


@app.get("/api/v1/health")
def health_check():
    """Part A10.3 — health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.app_env,
    }
