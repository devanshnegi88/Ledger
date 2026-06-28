"""
Ledger Entry — the atomic, immutable unit of the audit trail (Part A2.3).

Immutability is enforced at THREE layers (defence in depth, Part A2.2):
  1. Application layer: no update_entry()/delete_entry() service method exists.
  2. ORM layer: SQLAlchemy events block UPDATE/DELETE on POSTED rows (see events.py).
  3. Database layer: BEFORE UPDATE/DELETE triggers raise exceptions
     (see migrations/003_create_immutability_triggers.sql).

Hash chain: hash = SHA256(canonical_entry_json + previous_hash)
"""
import enum
import uuid
from uuid6 import uuid7
from sqlalchemy import (
    Column, String, Numeric, DateTime, Enum, ForeignKey, CheckConstraint,
    Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class EntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class EntryStatus(str, enum.Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    entry_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journals.id"), nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)

    entry_type = Column(Enum(EntryType), nullable=False)
    amount = Column(Numeric(19, 4), nullable=False)
    currency = Column(String(3), nullable=False)

    effective_date = Column(DateTime(timezone=True), nullable=False, index=True)
    posted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    created_by = Column(String(120), nullable=False)  # NOT NULL — Incident #12 fix
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)

    reference_type = Column(String(60), nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    narrative = Column(String(500))

    hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=True)

    metadata_json = Column(JSONB, default=dict)
    status = Column(Enum(EntryStatus), nullable=False, default=EntryStatus.POSTED)

    journal = relationship("Journal", back_populates="entries")
    account = relationship("Account")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        CheckConstraint("char_length(currency) = 3", name="ck_ledger_entries_currency_iso4217"),
        CheckConstraint("char_length(hash) = 64", name="ck_ledger_entries_hash_len"),
        Index("ix_ledger_entries_account_effective", "account_id", "effective_date"),
    )

    def __repr__(self) -> str:
        return f"<LedgerEntry {self.entry_id} {self.entry_type} {self.amount}{self.currency}>"
