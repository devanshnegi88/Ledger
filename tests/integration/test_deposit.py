"""
tests/integration/test_deposit.py
Requires a live PostgreSQL (see tests/conftest.py).
"""
from decimal import Decimal
from src.validators.schemas import DepositBankRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.models.transaction import TransactionStatus


def test_deposit_creates_balanced_journal(db_session, unique_idempotency_key):
    request = DepositBankRequest(
        account_code="cust-alice-001",
        amount=Decimal("5000.0000"),
        currency="INR",
        idempotency_key=unique_idempotency_key,
        created_by="alice",
    )

    txn = process_deposit_bank(db_session, request)
    db_session.commit()

    assert txn.status == TransactionStatus.POSTED

    wallet = get_or_create_customer_wallet(db_session, "cust-alice-001", "INR")
    balance = get_cached_balance(db_session, wallet.id)
    assert balance == Decimal("5000.0000")


def test_duplicate_idempotency_key_does_not_double_post(db_session, unique_idempotency_key):
    request = DepositBankRequest(
        account_code="cust-bob-001",
        amount=Decimal("1000.0000"),
        currency="INR",
        idempotency_key=unique_idempotency_key,
        created_by="bob",
    )

    txn1 = process_deposit_bank(db_session, request)
    db_session.commit()

    # Retry with the exact same request — must replay, not double-post (Incident #2).
    txn2 = process_deposit_bank(db_session, request)
    db_session.commit()

    assert txn1.id == txn2.id

    wallet = get_or_create_customer_wallet(db_session, "cust-bob-001", "INR")
    balance = get_cached_balance(db_session, wallet.id)
    assert balance == Decimal("1000.0000")  # NOT 2000 — proves no double-posting
