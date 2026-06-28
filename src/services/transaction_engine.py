"""
src/services/transaction_engine.py

Enforces the transaction lifecycle state machine (Part A4.1):
INITIATED -> PROCESSING -> POSTED -> REVERSAL_PENDING -> REVERSED
                        -> FAILED
INITIATED -> REJECTED

This module wraps every transaction handler so that:
  - Idempotency is checked FIRST, before any business logic (Part A9.2).
  - State transitions are validated against ALLOWED_TRANSITIONS.
  - All journal entries from a handler commit atomically with the
    transaction's terminal state (POSTED or FAILED) — never partially.
"""
import hashlib
import json
import uuid
from uuid6 import uuid7
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy.orm import Session

from src.config.database import db_transaction
from src.config.settings import settings
from src.models.transaction import Transaction, TransactionStatus, ALLOWED_TRANSITIONS
from src.models.audit_log import IdempotencyKey
from src.utils.exceptions import IdempotencyConflictError, InvalidStateTransitionError, LedgerError


def _request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def transition(transaction: Transaction, new_status: TransactionStatus) -> None:
    allowed = ALLOWED_TRANSITIONS.get(transaction.status, set())
    if new_status not in allowed:
        raise InvalidStateTransitionError(
            f"Cannot transition transaction {transaction.id} from "
            f"{transaction.status} to {new_status}"
        )
    transaction.status = new_status


def execute_transaction(
    *,
    db: Session,
    transaction_type,
    endpoint: str,
    user_id: str,
    idempotency_key: str,
    request_payload: dict,
    handler: Callable[[Session, Transaction], None],
) -> Transaction:
    """
    Generic transaction execution wrapper used by every transaction-type
    handler. `handler(db, transaction)` must create journal entries via
    journal_entry_service.create_journal_entry() and may raise LedgerError
    subclasses to signal a business rule failure.
    """
    req_hash = _request_hash(request_payload)

    # --- Idempotency check (Part A9.2) — first operation, before any business logic ---
    existing_key = db.execute(
        "SELECT status, response_status, response_body, request_hash "
        "FROM idempotency_keys WHERE user_id = :uid AND key = :key AND expires_at > now()",
        {"uid": user_id, "key": idempotency_key},
    ).first()

    if existing_key is not None:
        existing_status, resp_status, resp_body, existing_hash = existing_key
        if existing_hash != req_hash:
            raise IdempotencyConflictError(
                "Idempotency key reused with a different request body"
            )
        if existing_status == "COMPLETED":
            # Replay — return the original transaction without reprocessing.
            txn_id = (resp_body or {}).get("transaction_id")
            if txn_id:
                return db.get(Transaction, uuid.UUID(txn_id))
        # status == PROCESSING or FAILED -> fall through and retry below.

    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.idempotency_key_ttl_hours)
    db.execute(
        """
        INSERT INTO idempotency_keys (id, key, user_id, endpoint, request_hash, status, created_at, expires_at)
        VALUES (:id, :key, :uid, :endpoint, :hash, 'PROCESSING', now(), :expires_at)
        ON CONFLICT DO NOTHING
        """,
        {
            "id": str(uuid7()), "key": idempotency_key, "uid": user_id,
            "endpoint": endpoint, "hash": req_hash, "expires_at": expires_at,
        },
    )

    transaction = Transaction(
        id=uuid7(),
        transaction_type=transaction_type,
        status=TransactionStatus.INITIATED,
        idempotency_key=idempotency_key,
        request_payload=request_payload,
        created_by=user_id,
    )
    db.add(transaction)
    db.flush()

    transition(transaction, TransactionStatus.PROCESSING)

    try:
        handler(db, transaction)
        transition(transaction, TransactionStatus.POSTED)
        db.execute(
            "UPDATE idempotency_keys SET status='COMPLETED', response_status=200, "
            "response_body=:body WHERE user_id=:uid AND key=:key",
            {"body": json.dumps({"transaction_id": str(transaction.id)}),
             "uid": user_id, "key": idempotency_key},
        )
    except LedgerError as exc:
        transaction.status = TransactionStatus.FAILED
        transaction.error_message = str(exc)
        db.execute(
            "UPDATE idempotency_keys SET status='FAILED' WHERE user_id=:uid AND key=:key",
            {"uid": user_id, "key": idempotency_key},
        )
        raise

    return transaction
