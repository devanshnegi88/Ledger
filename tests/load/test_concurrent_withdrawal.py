"""
tests/load/test_concurrent_withdrawal.py

Day 7 acceptance criteria: 50 concurrent withdrawals of INR 500 each
against an account with INR 10,000 balance. Exactly 20 must succeed, 30
must fail with InsufficientBalanceError, the account must never go
negative, and there must be zero deadlocks.

Uses a thread pool with one DB session per thread (SQLAlchemy sessions are
not thread-safe to share) to genuinely exercise PostgreSQL's row locking
under concurrent load — this is NOT meaningful against SQLite.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.validators.schemas import DepositBankRequest, WithdrawalRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.withdrawal import process_withdrawal
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.utils.exceptions import InsufficientBalanceError


def _attempt_withdrawal(customer_ref: str, idem_key: str) -> str:
    """Runs in its own thread with its own engine/session — returns 'OK' or 'INSUFFICIENT'."""
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        process_withdrawal(db, WithdrawalRequest(
            account_code=customer_ref, amount=Decimal("500.0000"),
            currency="INR", idempotency_key=idem_key, created_by="load-test",
        ))
        db.commit()
        return "OK"
    except InsufficientBalanceError:
        db.rollback()
        return "INSUFFICIENT"
    finally:
        db.close()
        engine.dispose()


def test_50_concurrent_withdrawals_no_double_spend(db_engine, db_session):
    customer_ref = f"cust-load-{uuid.uuid4().hex[:8]}"

    process_deposit_bank(db_session, DepositBankRequest(
        account_code=customer_ref, amount=Decimal("10000.0000"), currency="INR",
        idempotency_key=f"seed-{uuid.uuid4().hex}", created_by="load-test",
    ))
    db_session.commit()

    results = []
    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [
            pool.submit(_attempt_withdrawal, customer_ref, f"wd-{uuid.uuid4().hex}")
            for _ in range(50)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    succeeded = results.count("OK")
    failed = results.count("INSUFFICIENT")

    assert succeeded == 20, f"Expected exactly 20 successes, got {succeeded}"
    assert failed == 30, f"Expected exactly 30 insufficient-balance failures, got {failed}"

    wallet = get_or_create_customer_wallet(db_session, customer_ref, "INR")
    final_balance = get_cached_balance(db_session, wallet.id)
    assert final_balance == Decimal("0.0000")
    assert final_balance >= 0, "Account must never go negative — double-spend prevention failed"
