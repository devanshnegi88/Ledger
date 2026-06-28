"""
audit_logs — structured, append-only record of every state-changing action
(separate from ledger_entries; this captures API-level/operational events,
e.g. account closures, manual reversals, admin actions).

idempotency_keys — Part A9: exactly-once processing guarantee.
"""
import uuid
from uuid6 import uuid7
from sqlalchemy import Column, String, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from src.config.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    actor = Column(String(120), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    request_id = Column(String(60), nullable=True, index=True)
    details = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    key = Column(String(128), nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    endpoint = Column(String(150), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default="PROCESSING")  # PROCESSING|COMPLETED|FAILED
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
