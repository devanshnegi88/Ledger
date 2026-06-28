"""
Reversal — records a corrective journal that mirrors an original transaction
(Part A5 / A5.3). Duplicate reversal attempts are blocked at the DB level via
UNIQUE(original_transaction_id, reversal_idempotency_key).
"""
import enum
import uuid
from uuid6 import uuid7
from sqlalchemy import (
    Column, String, Numeric, DateTime, Enum, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


class ReversalType(str, enum.Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"


class FeeRefundPolicy(str, enum.Enum):
    PROPORTIONAL = "PROPORTIONAL"
    FULL = "FULL"
    NONE = "NONE"


class Reversal(Base):
    __tablename__ = "reversals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    original_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, index=True)
    reversal_transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    reversal_idempotency_key = Column(String(128), nullable=False)
    reversal_type = Column(Enum(ReversalType), nullable=False)
    fee_refund_policy = Column(Enum(FeeRefundPolicy), nullable=True)
    refunded_amount = Column(Numeric(19, 4), nullable=False)
    reason = Column(String(500))
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "original_transaction_id", "reversal_idempotency_key",
            name="uq_reversal_original_idempotency",
        ),
    )

    def __repr__(self) -> str:
        return f"<Reversal orig={self.original_transaction_id} type={self.reversal_type}>"
