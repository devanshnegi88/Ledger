"""
src/routes/audit.py
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query

from src.controllers.audit_controller import handle_audit_verify, handle_audit_hash_chain_anomalies

router = APIRouter(tags=["audit"])


@router.get("/api/v1/audit/verify")
def audit_verify(
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
):
    return handle_audit_verify(from_date, to_date)


@router.get("/api/v1/audit/hash-chain")
def audit_hash_chain():
    return handle_audit_hash_chain_anomalies()
