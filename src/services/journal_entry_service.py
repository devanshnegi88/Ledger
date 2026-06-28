"""
src/services/journal_entry_service.py

Core journal entry creation logic (Day 3 / Part A1.3, A2, A9).

Responsibilities:
  1. Validate SUM(debits) == SUM(credits) — reject unbalanced journals.
  2. Resolve account_code -> account_id.
  3. Lock the global hash-chain pointer (SELECT ... FOR UPDATE) and compute
     each entry's hash sequentially against it.
  4. Persist the Journal + all LedgerEntry rows atomically (single DB
     transaction — Anti-Pattern #5 guard).
  5. Update balance_snapshots for every affected account.

This module deliberately contains NO transaction-type-specific logic —
that lives in services/transactionHandlers/*. This keeps business rules
testable independently of the ledger-persistence mechanics (Anti-Pattern #11).
"""
import uuid
from uuid6 import uuid7
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.journal import Journal
from src.models.ledger_entry import LedgerEntry, EntryType, EntryStatus
from src.models.transaction import Transaction, TransactionStatus
from src.utils.money import to_money, sum_money
from src.utils.hash import compute_entry_hash, entry_fields_for_hash
from src.utils.exceptions import UnbalancedJournalError, AccountNotFoundError


@dataclass
class LineInput:
    account_code: str
    entry_type: EntryType
    amount: Decimal
    currency: str
    narrative: Optional[str] = None


def _assert_balanced(lines: List[LineInput]) -> None:
    """
    Part A1.3 golden rule: SUM(debits) must exactly equal SUM(credits).

    Validated PER CURRENCY, not as one mixed total — a multi-currency
    journal (e.g. FX Conversion, Part A3.2) is only meaningful if each
    currency's own debits and credits balance independently. Summing raw
    numbers across different currencies (5 USD + 400 INR) would be
    accounting nonsense even if the totals happened to match numerically.
    """
    by_currency: dict = {}
    for line in lines:
        by_currency.setdefault(line.currency, {"debit": Decimal("0"), "credit": Decimal("0")})
        if line.entry_type == EntryType.DEBIT:
            by_currency[line.currency]["debit"] += line.amount
        else:
            by_currency[line.currency]["credit"] += line.amount

    for currency, totals in by_currency.items():
        debits = to_money(totals["debit"])
        credits = to_money(totals["credit"])
        if debits != credits:
            raise UnbalancedJournalError(
                f"Journal is unbalanced for {currency}: total debits={debits} != total credits={credits}"
            )


def _resolve_account(db: Session, account_code: str) -> Account:
    account = db.execute(
        select(Account).where(Account.account_code == account_code)
    ).scalar_one_or_none()
    if account is None:
        raise AccountNotFoundError(f"Account with code '{account_code}' does not exist")
    return account


def create_journal_entry(
    db: Session,
    *,
    transaction: Transaction,
    lines: List[LineInput],
    reference_type: str,
    reference_id: Optional[uuid.UUID],
    created_by: str,
    narrative: Optional[str] = None,
    effective_date: Optional[datetime] = None,
) -> Journal:
    """
    Create and persist a balanced journal entry with hash-chained ledger lines.

    Must be called within an active db transaction (see db_transaction()).
    Caller is responsible for commit/rollback (journal_entry_service does not
    commit itself, so it can be composed into larger compound operations —
    Part A9.3 — without partial commits).
    """
    if len(lines) < 2:
        raise UnbalancedJournalError("A journal entry must have at least two lines")

    _assert_balanced(lines)

    effective_date = effective_date or datetime.now(timezone.utc)

    journal = Journal(
        id=uuid7(),
        journal_reference=f"JE-{uuid7().hex[:16].upper()}",
        transaction_id=transaction.id,
        narrative=narrative,
        created_by=created_by,
        metadata_json={},
    )
    db.add(journal)
    db.flush()  # assign journal.id to DB without committing

    # --- Lock the global hash chain pointer for the duration of this insert ---
    # SELECT ... FOR UPDATE serialises concurrent appends so the chain never forks.
    chain_state = db.execute(
        "SELECT last_hash FROM hash_chain_state WHERE id = 1 FOR UPDATE"
    ).first()
    previous_hash = chain_state[0] if chain_state else ("0" * 64)

    created_entries: List[LedgerEntry] = []

    for line in lines:
        account = _resolve_account(db, line.account_code)
        entry_id = uuid7()
        amount = to_money(line.amount)

        entry = LedgerEntry(
            entry_id=entry_id,
            journal_id=journal.id,
            account_id=account.id,
            entry_type=line.entry_type,
            amount=amount,
            currency=line.currency,
            effective_date=effective_date,
            created_by=created_by,
            reference_type=reference_type,
            reference_id=reference_id,
            narrative=line.narrative or narrative,
            status=EntryStatus.POSTED,
        )

        hashable_fields = entry_fields_for_hash(entry)
        entry.previous_hash = previous_hash
        entry.hash = compute_entry_hash(hashable_fields, previous_hash)
        previous_hash = entry.hash  # chain continues to the next line

        db.add(entry)
        created_entries.append(entry)

    db.flush()

    # Advance the global chain pointer to the last entry's hash.
    db.execute(
        "UPDATE hash_chain_state SET last_hash = :h, last_entry_id = :eid, updated_at = now() WHERE id = 1",
        {"h": previous_hash, "eid": str(created_entries[-1].entry_id)},
    )

    # Update balance snapshots (Anti-Pattern #2 guard: derived, not user-mutable)
    from src.services.balance_service import apply_entries_to_snapshot
    apply_entries_to_snapshot(db, created_entries)

    return journal
