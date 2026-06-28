"""
src/services/reversal_service.py

Part A5 — Reversals, Refunds & the No-Mutation Principle. Day 8.

Full reversal: mirrors every POSTED ledger line of the original transaction
(DEBIT<->CREDIT swap), referencing the original. Partial refund: scales
principal lines by (refund_amount / original_amount) and applies the
selected fee policy to any fee-revenue line.

Concurrency: an advisory lock keyed on the original_transaction_id
serialises concurrent reversal attempts against the SAME original
transaction (Case Study #4 — Razorpay concurrent refund race), so two
simultaneous refund requests can never both pass the
"already refunded?" check before either commits.
"""
import uuid
from uuid6 import uuid7
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType, TransactionStatus
from src.models.journal import Journal
from src.models.ledger_entry import LedgerEntry, EntryType, EntryStatus
from src.models.reversal import Reversal, ReversalType, FeeRefundPolicy
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import transition
from src.services.account_service import POOLED_ASSET_CODE_BY_CURRENCY
from src.validators.schemas import FullReversalRequest, PartialRefundRequest
from src.utils.exceptions import (
    LedgerError, RefundExceedsOriginalError, InvalidStateTransitionError,
)
from src.utils.money import to_money

FEE_REVENUE_ACCOUNT_CODES = {"4001", "4010"}  # Transaction Fee Revenue, Interchange Revenue


def _advisory_lock_for_transaction(db: Session, transaction_id: uuid.UUID) -> None:
    key = int(uuid.UUID(str(transaction_id)).int & 0x7FFFFFFFFFFFFFFF)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def _get_original_entries(db: Session, original_transaction_id: uuid.UUID) -> List[LedgerEntry]:
    return list(db.execute(
        select(LedgerEntry)
        .join(Journal, Journal.id == LedgerEntry.journal_id)
        .where(
            Journal.transaction_id == original_transaction_id,
            LedgerEntry.status == EntryStatus.POSTED,
        )
        .order_by(LedgerEntry.posted_at)
    ).scalars().all())


def _existing_reversal(db: Session, original_transaction_id: uuid.UUID, key: str) -> Optional[Reversal]:
    return db.execute(
        select(Reversal).where(
            Reversal.original_transaction_id == original_transaction_id,
            Reversal.reversal_idempotency_key == key,
        )
    ).scalar_one_or_none()


def _total_already_refunded(db: Session, original_transaction_id: uuid.UUID) -> Decimal:
    rows = db.execute(
        select(Reversal.refunded_amount).where(Reversal.original_transaction_id == original_transaction_id)
    ).scalars().all()
    total = Decimal("0.0000")
    for amount in rows:
        total += Decimal(amount)
    return total


def _has_full_reversal(db: Session, original_transaction_id: uuid.UUID) -> bool:
    return db.execute(
        select(Reversal.id).where(
            Reversal.original_transaction_id == original_transaction_id,
            Reversal.reversal_type == ReversalType.FULL,
        )
    ).first() is not None


def process_full_reversal(db: Session, request: FullReversalRequest) -> Transaction:
    original_id = uuid.UUID(request.original_transaction_id)

    # Serialise concurrent reversal attempts against this original transaction.
    _advisory_lock_for_transaction(db, original_id)

    existing = _existing_reversal(db, original_id, request.idempotency_key)
    if existing is not None:
        return db.get(Transaction, existing.reversal_transaction_id)

    if _has_full_reversal(db, original_id):
        raise RefundExceedsOriginalError(
            f"Transaction {original_id} has already been fully reversed"
        )

    original_txn = db.get(Transaction, original_id)
    if original_txn is None:
        raise LedgerError(f"Original transaction {original_id} not found")
    if original_txn.status != TransactionStatus.POSTED:
        raise InvalidStateTransitionError(
            f"Cannot reverse transaction {original_id} in status {original_txn.status}"
        )

    original_entries = _get_original_entries(db, original_id)
    if not original_entries:
        raise LedgerError(f"No posted ledger entries found for transaction {original_id}")

    pooled_codes = set(POOLED_ASSET_CODE_BY_CURRENCY.values())
    refunded_principal = sum(
        (e.amount for e in original_entries
         if e.entry_type == EntryType.DEBIT and e.account.account_code not in FEE_REVENUE_ACCOUNT_CODES
         and e.account.account_code not in pooled_codes),
        Decimal("0.0000"),
    ) or original_entries[0].amount

    reversal_txn = Transaction(
        id=uuid7(),
        transaction_type=TransactionType.REFUND_FULL,
        status=TransactionStatus.INITIATED,
        idempotency_key=request.idempotency_key,
        request_payload={"original_transaction_id": str(original_id), "reason": request.reason},
        created_by=request.created_by,
    )
    db.add(reversal_txn)
    db.flush()
    transition(reversal_txn, TransactionStatus.PROCESSING)

    mirror_lines = [
        LineInput(
            account_code=entry.account.account_code,
            entry_type=EntryType.CREDIT if entry.entry_type == EntryType.DEBIT else EntryType.DEBIT,
            amount=entry.amount,
            currency=entry.currency,
            narrative=f"Reversal of {entry.entry_id}",
        )
        for entry in original_entries
    ]

    create_journal_entry(
        db,
        transaction=reversal_txn,
        lines=mirror_lines,
        reference_type="REVERSAL_FULL",
        reference_id=original_id,
        created_by=request.created_by,
        narrative=f"Full reversal of {original_id}: {request.reason}",
    )

    transition(reversal_txn, TransactionStatus.POSTED)

    # Move the ORIGINAL transaction through its own terminal reversal states.
    transition(original_txn, TransactionStatus.REVERSAL_PENDING)
    transition(original_txn, TransactionStatus.REVERSED)

    db.add(Reversal(
        id=uuid7(),
        original_transaction_id=original_id,
        reversal_transaction_id=reversal_txn.id,
        reversal_idempotency_key=request.idempotency_key,
        reversal_type=ReversalType.FULL,
        fee_refund_policy=None,
        refunded_amount=to_money(refunded_principal),
        reason=request.reason,
        created_by=request.created_by,
    ))

    return reversal_txn


def process_partial_refund(db: Session, request: PartialRefundRequest) -> Transaction:
    original_id = uuid.UUID(request.original_transaction_id)

    _advisory_lock_for_transaction(db, original_id)

    existing = _existing_reversal(db, original_id, request.idempotency_key)
    if existing is not None:
        return db.get(Transaction, existing.reversal_transaction_id)

    original_txn = db.get(Transaction, original_id)
    if original_txn is None:
        raise LedgerError(f"Original transaction {original_id} not found")
    if original_txn.status not in (TransactionStatus.POSTED,):
        raise InvalidStateTransitionError(
            f"Cannot refund transaction {original_id} in status {original_txn.status}"
        )

    original_entries = _get_original_entries(db, original_id)
    if not original_entries:
        raise LedgerError(f"No posted ledger entries found for transaction {original_id}")

    original_amount = Decimal(str(original_txn.request_payload.get("amount", "0")))
    if original_amount <= 0:
        # Fall back to the largest single line amount as a proxy for "principal".
        original_amount = max((e.amount for e in original_entries), default=Decimal("0"))

    already_refunded = _total_already_refunded(db, original_id)
    if already_refunded + request.refund_amount > original_amount:
        raise RefundExceedsOriginalError(
            f"Refund of {request.refund_amount} would bring total refunds to "
            f"{already_refunded + request.refund_amount}, exceeding original amount {original_amount}"
        )

    ratio = (request.refund_amount / original_amount) if original_amount > 0 else Decimal("0")

    original_fee_line = next(
        (e for e in original_entries if e.account.account_code in FEE_REVENUE_ACCOUNT_CODES), None
    )
    if request.fee_refund_policy == "PROPORTIONAL":
        fee_refund = to_money((original_fee_line.amount * ratio)) if original_fee_line else Decimal("0")
    elif request.fee_refund_policy == "FULL":
        fee_refund = original_fee_line.amount if original_fee_line else Decimal("0")
    else:  # NONE
        fee_refund = Decimal("0")

    reversal_txn = Transaction(
        id=uuid7(),
        transaction_type=TransactionType.REFUND_PARTIAL,
        status=TransactionStatus.INITIATED,
        idempotency_key=request.idempotency_key,
        request_payload={
            "original_transaction_id": str(original_id),
            "refund_amount": str(request.refund_amount),
            "fee_refund_policy": request.fee_refund_policy,
            "reason": request.reason,
        },
        created_by=request.created_by,
    )
    db.add(reversal_txn)
    db.flush()
    transition(reversal_txn, TransactionStatus.PROCESSING)

    mirror_lines = []
    for entry in original_entries:
        if entry.account.account_code in FEE_REVENUE_ACCOUNT_CODES:
            amount = fee_refund
        else:
            amount = to_money(entry.amount * ratio)
        if amount <= 0:
            continue
        mirror_lines.append(LineInput(
            account_code=entry.account.account_code,
            entry_type=EntryType.CREDIT if entry.entry_type == EntryType.DEBIT else EntryType.DEBIT,
            amount=amount,
            currency=entry.currency,
            narrative=f"Partial refund ({request.fee_refund_policy} fee policy) of {entry.entry_id}",
        ))

    create_journal_entry(
        db,
        transaction=reversal_txn,
        lines=mirror_lines,
        reference_type="REVERSAL_PARTIAL",
        reference_id=original_id,
        created_by=request.created_by,
        narrative=f"Partial refund of {original_id}: {request.reason}",
    )

    transition(reversal_txn, TransactionStatus.POSTED)

    db.add(Reversal(
        id=uuid7(),
        original_transaction_id=original_id,
        reversal_transaction_id=reversal_txn.id,
        reversal_idempotency_key=request.idempotency_key,
        reversal_type=ReversalType.PARTIAL,
        fee_refund_policy=FeeRefundPolicy(request.fee_refund_policy),
        refunded_amount=to_money(request.refund_amount),
        reason=request.reason,
        created_by=request.created_by,
    ))

    return reversal_txn
