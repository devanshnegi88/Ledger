"""
src/services/balance_service.py

Balance derivation (Part A4.3 "Ledger Balance as Aggregate" + Day 4).

The canonical balance of an account is ALWAYS derivable from
SUM(debit ledger_entries) - SUM(credit ledger_entries), adjusted for the
account's normal_balance direction. `balance_snapshots` is purely a
read-optimised cache populated from that derivation — it is never the
source of truth and is never mutated directly by transaction handlers
(Anti-Pattern #2 guard).
"""
from decimal import Decimal
from typing import List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.models.account import Account, AccountType, DEBIT_NORMAL_TYPES
from src.models.ledger_entry import LedgerEntry, EntryType, EntryStatus


def compute_account_balance(db: Session, account_id) -> Decimal:
    """
    Recompute an account's balance directly from POSTED ledger entries.
    This is the authoritative calculation — used to verify/repair snapshots.
    """
    account = db.get(Account, account_id)
    if account is None:
        return Decimal("0.0000")

    debit_total = db.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == EntryType.DEBIT,
            LedgerEntry.status == EntryStatus.POSTED,
        )
    ).scalar_one()
    credit_total = db.execute(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.account_id == account_id,
            LedgerEntry.entry_type == EntryType.CREDIT,
            LedgerEntry.status == EntryStatus.POSTED,
        )
    ).scalar_one()

    debit_total = Decimal(debit_total)
    credit_total = Decimal(credit_total)

    if account.account_type in DEBIT_NORMAL_TYPES:
        return debit_total - credit_total
    return credit_total - debit_total


def apply_entries_to_snapshot(db: Session, entries: List[LedgerEntry]) -> None:
    """
    Incrementally update balance_snapshots for every account touched by a
    freshly-inserted batch of entries. Uses UPSERT semantics so the snapshot
    table self-heals even if a row didn't exist yet.
    """
    touched_account_ids = {e.account_id for e in entries}
    for account_id in touched_account_ids:
        new_balance = compute_account_balance(db, account_id)
        account = db.get(Account, account_id)
        last_entry = max((e for e in entries if e.account_id == account_id),
                          key=lambda e: e.posted_at or 0, default=None)

        db.execute(
            """
            INSERT INTO balance_snapshots (account_id, balance, currency, last_entry_id, updated_at)
            VALUES (:account_id, :balance, :currency, :last_entry_id, now())
            ON CONFLICT (account_id) DO UPDATE
            SET balance = :balance, last_entry_id = :last_entry_id, updated_at = now()
            """,
            {
                "account_id": str(account_id),
                "balance": str(new_balance),
                "currency": account.currency if account else "INR",
                "last_entry_id": str(last_entry.entry_id) if last_entry else None,
            },
        )


def get_cached_balance(db: Session, account_id) -> Decimal:
    """Fast read path — falls back to authoritative computation on cache miss."""
    row = db.execute(
        "SELECT balance FROM balance_snapshots WHERE account_id = :account_id",
        {"account_id": str(account_id)},
    ).first()
    if row is None:
        return compute_account_balance(db, account_id)
    return Decimal(row[0])
