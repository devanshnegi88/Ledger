"""
tests/integration/test_withdrawal.py
"""
from decimal import Decimal
import pytest

from src.validators.schemas import DepositBankRequest, WithdrawalRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.withdrawal import process_withdrawal
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.utils.exceptions import InsufficientBalanceError


def test_withdrawal_succeeds_with_sufficient_balance(db_session, unique_idempotency_key):
    deposit_req = DepositBankRequest(
        account_code="cust-carol-001", amount=Decimal("2000.0000"),
        currency="INR", idempotency_key=f"dep-{unique_idempotency_key}", created_by="carol",
    )
    process_deposit_bank(db_session, deposit_req)
    db_session.commit()

    withdraw_req = WithdrawalRequest(
        account_code="cust-carol-001", amount=Decimal("500.0000"),
        currency="INR", idempotency_key=f"wd-{unique_idempotency_key}", created_by="carol",
    )
    process_withdrawal(db_session, withdraw_req)
    db_session.commit()

    wallet = get_or_create_customer_wallet(db_session, "cust-carol-001", "INR")
    balance = get_cached_balance(db_session, wallet.id)
    assert balance == Decimal("1500.0000")


def test_withdrawal_rejected_when_balance_insufficient(db_session, unique_idempotency_key):
    deposit_req = DepositBankRequest(
        account_code="cust-dave-001", amount=Decimal("100.0000"),
        currency="INR", idempotency_key=f"dep-{unique_idempotency_key}", created_by="dave",
    )
    process_deposit_bank(db_session, deposit_req)
    db_session.commit()

    withdraw_req = WithdrawalRequest(
        account_code="cust-dave-001", amount=Decimal("5000.0000"),
        currency="INR", idempotency_key=f"wd-{unique_idempotency_key}", created_by="dave",
    )
    with pytest.raises(InsufficientBalanceError):
        process_withdrawal(db_session, withdraw_req)
    db_session.rollback()
