"""
tests/integration/test_fx_conversion.py
"""
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import pytest

from src.validators.schemas import DepositBankRequest, FXConversionRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.fx_conversion import process_fx_conversion
from src.services.exchange_rate_service import record_rate_snapshot
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.services.trial_balance_service import generate_trial_balance
from src.utils.exceptions import StaleRateError


def test_fx_conversion_creates_balanced_journal_per_currency(db_session, unique_idempotency_key):
    process_deposit_bank(db_session, DepositBankRequest(
        account_code="cust-fx-001", amount=Decimal("1000.0000"), currency="USD",
        idempotency_key=f"dep-{unique_idempotency_key}", created_by="fxuser",
    ))
    db_session.commit()

    fx_req = FXConversionRequest(
        customer_account_code="cust-fx-001",
        source_currency="USD",
        target_currency="INR",
        source_amount=Decimal("100.0000"),
        fx_markup_bps=50,
        idempotency_key=unique_idempotency_key,
        created_by="fxuser",
    )
    process_fx_conversion(db_session, fx_req)
    db_session.commit()

    usd_wallet = get_or_create_customer_wallet(db_session, "cust-fx-001", "USD")
    inr_wallet = get_or_create_customer_wallet(db_session, "cust-fx-001", "INR")

    assert get_cached_balance(db_session, usd_wallet.id) == Decimal("900.0000")
    assert get_cached_balance(db_session, inr_wallet.id) > Decimal("0")

    report = generate_trial_balance(db_session)
    assert report.is_balanced


def test_stale_rate_is_rejected(db_session, unique_idempotency_key):
    # Insert a deliberately stale snapshot (captured 48h ago) for a currency
    # pair with no other valid snapshot, then attempt to convert.
    stale_time = datetime.now(timezone.utc) - timedelta(hours=48)
    db_session.execute(
        "DELETE FROM exchange_rate_snapshots WHERE base_currency='GBP' AND quote_currency='INR'"
    )
    db_session.execute(
        """
        INSERT INTO exchange_rate_snapshots
          (snapshot_id, base_currency, quote_currency, rate, inverse_rate, source, captured_at, valid_from, valid_until)
        VALUES (gen_random_uuid(), 'GBP', 'INR', 105.0, 0.00952381, 'TEST', :captured_at, :captured_at, NULL)
        """,
        {"captured_at": stale_time},
    )
    db_session.commit()

    process_deposit_bank(db_session, DepositBankRequest(
        account_code="cust-fx-002", amount=Decimal("500.0000"), currency="GBP",
        idempotency_key=f"dep-{unique_idempotency_key}", created_by="fxuser2",
    ))
    db_session.commit()

    fx_req = FXConversionRequest(
        customer_account_code="cust-fx-002",
        source_currency="GBP",
        target_currency="INR",
        source_amount=Decimal("50.0000"),
        idempotency_key=unique_idempotency_key,
        created_by="fxuser2",
    )
    with pytest.raises(StaleRateError):
        process_fx_conversion(db_session, fx_req)
    db_session.rollback()
