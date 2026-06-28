"""
tests/integration/test_reversal.py — Day 8
"""
from decimal import Decimal
import uuid
import pytest

from src.validators.schemas import (
    DepositBankRequest, P2PTransferRequest, FullReversalRequest, PartialRefundRequest,
)
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
from src.services.reversal_service import process_full_reversal, process_partial_refund
from src.services.balance_service import get_cached_balance
from src.services.account_service import get_or_create_customer_wallet
from src.services.trial_balance_service import generate_trial_balance
from src.models.transaction import TransactionStatus
from src.utils.exceptions import RefundExceedsOriginalError


def _seeded_p2p(db_session, sender, recipient, amount="1000.0000", fee="10.0000"):
    process_deposit_bank(db_session, DepositBankRequest(
        account_code=sender, amount=Decimal("5000.0000"), currency="INR",
        idempotency_key=f"seed-{uuid.uuid4().hex}", created_by="setup",
    ))
    db_session.commit()
    txn = process_p2p_transfer(db_session, P2PTransferRequest(
        sender_account_code=sender, recipient_account_code=recipient,
        amount=Decimal(amount), fee_amount=Decimal(fee), currency="INR",
        idempotency_key=f"p2p-{uuid.uuid4().hex}", created_by=sender,
    ))
    db_session.commit()
    return txn


def test_full_reversal_mirrors_original_and_restores_balances(db_session):
    sender = f"cust-rev-a-{uuid.uuid4().hex[:6]}"
    recipient = f"cust-rev-b-{uuid.uuid4().hex[:6]}"
    original_txn = _seeded_p2p(db_session, sender, recipient)

    sender_wallet = get_or_create_customer_wallet(db_session, sender, "INR")
    balance_after_transfer = get_cached_balance(db_session, sender_wallet.id)
    assert balance_after_transfer == Decimal("3990.0000")  # 5000 - 1000 - 10

    reversal_txn = process_full_reversal(db_session, FullReversalRequest(
        original_transaction_id=str(original_txn.id),
        reason="Customer dispute",
        idempotency_key=f"rev-{uuid.uuid4().hex}",
        created_by="ops-agent",
    ))
    db_session.commit()

    assert reversal_txn.status == TransactionStatus.POSTED

    db_session.refresh(original_txn) if hasattr(db_session, "refresh") else None
    refreshed = db_session.get(type(original_txn), original_txn.id)
    assert refreshed.status == TransactionStatus.REVERSED

    balance_after_reversal = get_cached_balance(db_session, sender_wallet.id)
    assert balance_after_reversal == Decimal("5000.0000")  # fully restored

    report = generate_trial_balance(db_session)
    assert report.is_balanced


def test_duplicate_full_reversal_is_rejected(db_session):
    sender = f"cust-rev-c-{uuid.uuid4().hex[:6]}"
    recipient = f"cust-rev-d-{uuid.uuid4().hex[:6]}"
    original_txn = _seeded_p2p(db_session, sender, recipient)

    process_full_reversal(db_session, FullReversalRequest(
        original_transaction_id=str(original_txn.id), reason="first reversal",
        idempotency_key=f"rev-{uuid.uuid4().hex}", created_by="ops-agent",
    ))
    db_session.commit()

    with pytest.raises(RefundExceedsOriginalError):
        process_full_reversal(db_session, FullReversalRequest(
            original_transaction_id=str(original_txn.id), reason="duplicate attempt",
            idempotency_key=f"rev-{uuid.uuid4().hex}", created_by="ops-agent",
        ))
    db_session.rollback()


def test_partial_refund_proportional_fee_policy(db_session):
    sender = f"cust-rev-e-{uuid.uuid4().hex[:6]}"
    recipient = f"cust-rev-f-{uuid.uuid4().hex[:6]}"
    original_txn = _seeded_p2p(db_session, sender, recipient, amount="1000.0000", fee="20.0000")

    refund_txn = process_partial_refund(db_session, PartialRefundRequest(
        original_transaction_id=str(original_txn.id),
        refund_amount=Decimal("500.0000"),  # 50% of original
        fee_refund_policy="PROPORTIONAL",
        reason="Partial dissatisfaction",
        idempotency_key=f"refund-{uuid.uuid4().hex}",
        created_by="ops-agent",
    ))
    db_session.commit()

    assert refund_txn.status == TransactionStatus.POSTED

    sender_wallet = get_or_create_customer_wallet(db_session, sender, "INR")
    # 5000 - 1000 - 20 (original) + 500 + 10 (50% proportional fee refund) = 4490
    assert get_cached_balance(db_session, sender_wallet.id) == Decimal("4490.0000")

    report = generate_trial_balance(db_session)
    assert report.is_balanced


def test_refund_exceeding_original_is_rejected(db_session):
    sender = f"cust-rev-g-{uuid.uuid4().hex[:6]}"
    recipient = f"cust-rev-h-{uuid.uuid4().hex[:6]}"
    original_txn = _seeded_p2p(db_session, sender, recipient, amount="1000.0000", fee="0")

    with pytest.raises(RefundExceedsOriginalError):
        process_partial_refund(db_session, PartialRefundRequest(
            original_transaction_id=str(original_txn.id),
            refund_amount=Decimal("1500.0000"),  # exceeds original 1000
            fee_refund_policy="NONE",
            reason="Should fail",
            idempotency_key=f"refund-{uuid.uuid4().hex}",
            created_by="ops-agent",
        ))
    db_session.rollback()
