"""
tests/load/test_concurrent_p2p.py

Day 7 deliverable: 20 concurrent P2P transfers between the SAME two
accounts, alternating direction (A->B and B->A), to exercise the
deterministic lock-ordering deadlock prevention in
concurrency_control.lock_accounts_for_update_ordered(). Without ordered
locking, opposite-direction concurrent transfers can deadlock.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.validators.schemas import DepositBankRequest, P2PTransferRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.utils.exceptions import InsufficientBalanceError


def _attempt_transfer(sender: str, recipient: str, idem_key: str) -> str:
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    db = SessionLocal()
    try:
        process_p2p_transfer(db, P2PTransferRequest(
            sender_account_code=sender, recipient_account_code=recipient,
            amount=Decimal("10.0000"), fee_amount=Decimal("0"),
            currency="INR", idempotency_key=idem_key, created_by="load-test",
        ))
        db.commit()
        return "OK"
    except InsufficientBalanceError:
        db.rollback()
        return "INSUFFICIENT"
    except Exception as exc:  # noqa: BLE001 — surfacing deadlocks explicitly for the assertion below
        db.rollback()
        if "deadlock" in str(exc).lower():
            return "DEADLOCK"
        raise
    finally:
        db.close()
        engine.dispose()


def test_20_concurrent_bidirectional_p2p_transfers_no_deadlock(db_engine, db_session):
    account_a = f"cust-load-a-{uuid.uuid4().hex[:8]}"
    account_b = f"cust-load-b-{uuid.uuid4().hex[:8]}"

    for acct in (account_a, account_b):
        process_deposit_bank(db_session, DepositBankRequest(
            account_code=acct, amount=Decimal("1000.0000"), currency="INR",
            idempotency_key=f"seed-{uuid.uuid4().hex}", created_by="load-test",
        ))
    db_session.commit()

    results = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = []
        for i in range(20):
            sender, recipient = (account_a, account_b) if i % 2 == 0 else (account_b, account_a)
            futures.append(pool.submit(_attempt_transfer, sender, recipient, f"p2p-{uuid.uuid4().hex}"))
        for future in as_completed(futures):
            results.append(future.result())

    assert "DEADLOCK" not in results, f"Deadlock detected: {results}"
    assert results.count("OK") == 20

    wallet_a = get_or_create_customer_wallet(db_session, account_a, "INR")
    wallet_b = get_or_create_customer_wallet(db_session, account_b, "INR")
    assert get_cached_balance(db_session, wallet_a.id) == Decimal("1000.0000")
    assert get_cached_balance(db_session, wallet_b.id) == Decimal("1000.0000")
