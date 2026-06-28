"""
Exchange Rate Snapshot — immutable record of an FX rate used in a transaction
(Part A3.1). Rates are never updated; a new conversion always inserts a new row.
"""
import uuid
from uuid6 import uuid7
from sqlalchemy import Column, String, Numeric, DateTime, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


class ExchangeRateSnapshot(Base):
    __tablename__ = "exchange_rate_snapshots"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    base_currency = Column(String(3), nullable=False, index=True)
    quote_currency = Column(String(3), nullable=False, index=True)
    rate = Column(Numeric(18, 8), nullable=False)
    inverse_rate = Column(Numeric(18, 8), nullable=False)
    source = Column(String(50), nullable=False)
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)  # NULL == currently valid

    __table_args__ = (
        CheckConstraint("rate > 0", name="ck_fx_rate_positive"),
        CheckConstraint("inverse_rate > 0", name="ck_fx_inverse_rate_positive"),
    )

    def __repr__(self) -> str:
        return f"<FXSnapshot {self.base_currency}/{self.quote_currency} @ {self.rate}>"
