"""
tests/integration/test_partitioning.py — Day 13

Verifies that after migration 007 partitions ledger_entries by
effective_date, normal reads/writes through the existing service layer
still work transparently (partitioning should be invisible to callers).
"""
from decimal import Decimal
import uuid

from src.validators.schemas import DepositBankRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet


def test_inserts_and_reads_work_transparently_across_partitions(db_session, unique_idempotency_key):
    cust = f"cust-part-{uuid.uuid4().hex[:8]}"
    process_deposit_bank(db_session, DepositBankRequest(
        account_code=cust, amount=Decimal("250.0000"), currency="INR",
        idempotency_key=unique_idempotency_key, created_by=cust,
    ))
    db_session.commit()

    wallet = get_or_create_customer_wallet(db_session, cust, "INR")
    assert get_cached_balance(db_session, wallet.id) == Decimal("250.0000")


def test_current_month_partition_exists(db_session):
    import datetime
    current_partition = f"ledger_entries_{datetime.date.today().strftime('%Y_%m')}"
    row = db_session.execute(
        "SELECT 1 FROM pg_class WHERE relname = :name", {"name": current_partition}
    ).first()
    assert row is not None, f"Expected partition {current_partition} to exist after migration 007"
