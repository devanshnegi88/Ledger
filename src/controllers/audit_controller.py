"""
src/controllers/audit_controller.py
"""
from typing import Optional
from datetime import datetime

from src.config.database import db_transaction
from src.services.audit_service import verify_hash_chain, detect_anomalies


def handle_audit_verify(from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> dict:
    with db_transaction() as db:
        result = verify_hash_chain(db, from_date, to_date)
        return {
            "total_entries_checked": result.total_entries_checked,
            "is_intact": result.is_intact,
            "first_break_entry_id": result.first_break_entry_id,
            "break_reason": result.break_reason,
        }


def handle_audit_hash_chain_anomalies() -> dict:
    with db_transaction() as db:
        findings = detect_anomalies(db)
        return {
            "anomaly_count": len(findings),
            "findings": [
                {"entry_id": f.entry_id, "account_id": f.account_id, "reason": f.reason}
                for f in findings
            ],
        }
