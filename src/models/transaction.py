"""
Transaction — the top-level request object that drives the state machine
(Part A4.1): INITIATED -> PROCESSING -> POSTED -> REVERSAL_PENDING -> REVERSED
                                     -> FAILED
            INITIATED -> REJECTED
"""
import enum
import uuid
from uuid6 import uuid7
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.config.database import Base


class TransactionType(str, enum.Enum):
    DEPOSIT_BANK = "DEPOSIT_BANK"
    DEPOSIT_CARD = "DEPOSIT_CARD"
    WITHDRAWAL = "WITHDRAWAL"
    P2P_TRANSFER = "P2P_TRANSFER"
    MERCHANT_QR_PAYMENT = "MERCHANT_QR_PAYMENT"
    MERCHANT_ONLINE_PAYMENT = "MERCHANT_ONLINE_PAYMENT"
    BILL_PAYMENT = "BILL_PAYMENT"
    INTEREST_ACCRUAL = "INTEREST_ACCRUAL"
    INTEREST_PAYOUT = "INTEREST_PAYOUT"
    FEE_DEDUCTION = "FEE_DEDUCTION"
    CASHBACK_CREDIT = "CASHBACK_CREDIT"
    PROMOTIONAL_CREDIT = "PROMOTIONAL_CREDIT"
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_EMI = "LOAN_EMI"
    FX_CONVERSION = "FX_CONVERSION"
    REFUND_FULL = "REFUND_FULL"
    REFUND_PARTIAL = "REFUND_PARTIAL"
    CHARGEBACK = "CHARGEBACK"
    REWARD_REDEMPTION = "REWARD_REDEMPTION"
    ACCOUNT_CLOSURE_SWEEP = "ACCOUNT_CLOSURE_SWEEP"


class TransactionStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    POSTED = "POSTED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    REVERSAL_PENDING = "REVERSAL_PENDING"
    REVERSED = "REVERSED"


# Allowed state transitions (Part A4.1) — enforced in transaction_engine.py
ALLOWED_TRANSITIONS = {
    TransactionStatus.INITIATED: {TransactionStatus.PROCESSING, TransactionStatus.REJECTED},
    TransactionStatus.PROCESSING: {TransactionStatus.POSTED, TransactionStatus.FAILED},
    TransactionStatus.POSTED: {TransactionStatus.REVERSAL_PENDING},
    TransactionStatus.REVERSAL_PENDING: {TransactionStatus.REVERSED},
    TransactionStatus.FAILED: set(),
    TransactionStatus.REJECTED: set(),
    TransactionStatus.REVERSED: set(),
}


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    status = Column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.INITIATED, index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    request_payload = Column(JSONB, nullable=False)
    error_message = Column(String(500), nullable=True)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    journals = relationship("Journal", back_populates="transaction")

    def __repr__(self) -> str:
        return f"<Transaction {self.id} {self.transaction_type} {self.status}>"
