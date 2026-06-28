"""
Journal model — groups related debit/credit ledger lines into one logical transaction.
"""
import uuid
from uuid6 import uuid7
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class Journal(Base):
    __tablename__ = "journals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    journal_reference = Column(String(60), unique=True, nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    narrative = Column(String(500))
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_json = Column(JSONB, default=dict)

    entries = relationship("LedgerEntry", back_populates="journal", cascade="all, delete-orphan")
    transaction = relationship("Transaction", back_populates="journals")

    def __repr__(self) -> str:
        return f"<Journal {self.journal_reference}>"
