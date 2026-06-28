"""
tests/integration/test_p2p_transfer.py
"""
from decimal import Decimal
import pytest

from src.validators.schemas import DepositBankRequest, P2PTransferRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.utils.exceptions import InsufficientBalanceError


def test_p2p_transfer_with_fee_is_balanced(db_session, unique_idempotency_key):
    process_deposit_bank(db_session, DepositBankRequest(
        account_code="cust-eve-001", amount=Decimal("10000.0000"),
        currency="INR", idempotency_key=f"dep-{unique_idempotency_key}", created_by="eve",
    ))
    db_session.commit()

    transfer_req = P2PTransferRequest(
        sender_account_code="cust-eve-001",
        recipient_account_code="cust-frank-001",
        amount=Decimal("3000.0000"),
        fee_amount=Decimal("10.0000"),
        currency="INR",
        idempotency_key=unique_idempotency_key,
        created_by="eve",
    )
    process_p2p_transfer(db_session, transfer_req)
    db_session.commit()

    sender_wallet = get_or_create_customer_wallet(db_session, "cust-eve-001", "INR")
    recipient_wallet = get_or_create_customer_wallet(db_session, "cust-frank-001", "INR")

    assert get_cached_balance(db_session, sender_wallet.id) == Decimal("6990.0000")  # 10000 - 3000 - 10
    assert get_cached_balance(db_session, recipient_wallet.id) == Decimal("3000.0000")


def test_p2p_transfer_rejected_when_sender_balance_insufficient(db_session, unique_idempotency_key):
    process_deposit_bank(db_session, DepositBankRequest(
        account_code="cust-grace-001", amount=Decimal("100.0000"),
        currency="INR", idempotency_key=f"dep-{unique_idempotency_key}", created_by="grace",
    ))
    db_session.commit()

    transfer_req = P2PTransferRequest(
        sender_account_code="cust-grace-001",
        recipient_account_code="cust-heidi-001",
        amount=Decimal("5000.0000"),
        fee_amount=Decimal("10.0000"),
        currency="INR",
        idempotency_key=unique_idempotency_key,
        created_by="grace",
    )
    with pytest.raises(InsufficientBalanceError):
        process_p2p_transfer(db_session, transfer_req)
    db_session.rollback()
