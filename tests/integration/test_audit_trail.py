"""
tests/integration/test_audit_trail.py — Day 11

Tamper-detection test: manually corrupt one entry's data (bypassing the
ORM/trigger layer via a direct, deliberately privileged raw connection
that simulates an attacker with DB access) and verify the hash chain
breaks at exactly that point.
"""
from decimal import Decimal
import uuid

from src.validators.schemas import DepositBankRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.audit_service import verify_hash_chain


def test_hash_chain_intact_after_normal_postings(db_session, unique_idempotency_key):
    for i in range(5):
        process_deposit_bank(db_session, DepositBankRequest(
            account_code=f"cust-audit-{i}", amount=Decimal("100.0000"), currency="INR",
            idempotency_key=f"{unique_idempotency_key}-{i}", created_by="audit-test",
        ))
    db_session.commit()

    result = verify_hash_chain(db_session)
    assert result.is_intact
    assert result.total_entries_checked >= 10


def test_tampered_entry_is_detected(db_session, unique_idempotency_key):
    process_deposit_bank(db_session, DepositBankRequest(
        account_code="cust-audit-tamper", amount=Decimal("777.0000"), currency="INR",
        idempotency_key=unique_idempotency_key, created_by="audit-test",
    ))
    db_session.commit()

    # Simulate an attacker with raw DB access bypassing the ORM and the
    # BEFORE UPDATE trigger's "status transition only" allowance by
    # directly rewriting the amount via a superuser-style session-local
    # trigger disable (this requires elevated privileges in real
    # Postgres — here we simply assert that IF the data were corrupted,
    # verification would catch it, by tampering with the hash field
    # itself, which the trigger does NOT protect against re-derivation
    # checks at the application layer).
    row = db_session.execute(
        "SELECT entry_id FROM ledger_entries WHERE idempotency_key IS NULL "
        "ORDER BY posted_at DESC LIMIT 1"
    ).first()
    # idempotency_key is on ledger_entries optionally; fetch most recent entry instead:
    row = db_session.execute(
        "SELECT entry_id FROM ledger_entries ORDER BY posted_at DESC LIMIT 1"
    ).first()
    entry_id = row[0]

    # Disable the trigger for this session only, to prove the APPLICATION-LEVEL
    # hash verification (not just the DB trigger) independently catches tampering.
    db_session.execute("ALTER TABLE ledger_entries DISABLE TRIGGER trg_prevent_ledger_entry_update")
    db_session.execute(
        "UPDATE ledger_entries SET amount = 999999.0000 WHERE entry_id = :eid",
        {"eid": entry_id},
    )
    db_session.execute("ALTER TABLE ledger_entries ENABLE TRIGGER trg_prevent_ledger_entry_update")
    db_session.commit()

    result = verify_hash_chain(db_session)
    assert result.is_intact is False
    assert result.first_break_entry_id == str(entry_id)

    db_session.rollback()
