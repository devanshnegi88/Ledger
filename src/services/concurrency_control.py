"""
src/services/concurrency_control.py

Part A4.3 — Concurrency Control / Double-Spend Prevention.
Day 7 deliverable.

Strategy chosen: **Pessimistic row locking** (`SELECT ... FOR UPDATE`) on
the `accounts` row, combined with **deterministic lock ordering** (always
lock accounts in ascending UUID order) to prevent deadlocks when a
transaction touches multiple accounts (e.g. P2P transfer locks both the
sender and recipient).

Why pessimistic locking over SERIALIZABLE SSI for V1:
  - Simpler to reason about and debug for a balance-check-then-write pattern.
  - Avoids the retry-on-abort complexity SERIALIZABLE requires under load.
  - ADR-002 documents the trade-off and benchmark plan for Day 7.

A SERIALIZABLE-isolation variant is also provided as `with_serializable_isolation`
for comparison/benchmarking (Case Study #4 — Razorpay concurrent refund analysis).
"""
import uuid
from typing import Iterable, List
from sqlalchemy.orm import Session
from sqlalchemy import text


def lock_account_for_update(db: Session, account_id: uuid.UUID) -> None:
    """Acquire an exclusive row lock on a single account's row."""
    db.execute(
        text("SELECT id FROM accounts WHERE id = :account_id FOR UPDATE"),
        {"account_id": str(account_id)},
    )


def lock_accounts_for_update_ordered(db: Session, account_ids: Iterable[uuid.UUID]) -> None:
    """
    Lock multiple accounts in a single, deterministic order (ascending UUID)
    to prevent deadlocks when concurrent transactions touch overlapping sets
    of accounts in different orders (e.g. A->B transfer vs B->A transfer
    happening concurrently).
    """
    ordered_ids: List[str] = sorted(str(a) for a in account_ids)
    if not ordered_ids:
        return
    db.execute(
        text("SELECT id FROM accounts WHERE id = ANY(:ids) ORDER BY id FOR UPDATE"),
        {"ids": ordered_ids},
    )


def acquire_advisory_lock(db: Session, lock_key: int) -> None:
    """
    Alternative strategy: session-level advisory lock keyed by a stable
    integer derived from the account_id. Useful when row-level locks would
    contend with unrelated read traffic on the accounts table.
    """
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})


def account_id_to_lock_key(account_id: uuid.UUID) -> int:
    """Deterministically fold a UUID into a 64-bit signed int for advisory locks."""
    return int(account_id.int & 0x7FFFFFFFFFFFFFFF)


def with_serializable_isolation(db: Session) -> None:
    """
    Set the current transaction's isolation level to SERIALIZABLE.
    PostgreSQL's SSI (Serializable Snapshot Isolation) detects write-skew
    conflicts at commit time and aborts one of the conflicting transactions
    with a serialization_failure error, which the caller must catch and retry.
    """
    db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
