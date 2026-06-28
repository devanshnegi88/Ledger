"""
tests/integration/test_trial_balance.py

Day 4 acceptance criteria: after inserting 100+ random transactions across
types 1-4, the trial balance's total debits must exactly equal total credits.
"""
import random
import uuid
from decimal import Decimal

from src.validators.schemas import (
    DepositBankRequest, WithdrawalRequest, P2PTransferRequest, FeeDeductionRequest,
)
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.withdrawal import process_withdrawal
from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
from src.services.transactionHandlers.fee_deduction import process_fee_deduction
from src.services.trial_balance_service import generate_trial_balance
from src.utils.exceptions import LedgerError


def test_trial_balance_after_100_random_transactions(db_session):
    customers = [f"cust-tb-{i:03d}" for i in range(10)]

    # Seed every customer with a starting balance so withdrawals/transfers
    # have something to draw from.
    for cust in customers:
        process_deposit_bank(db_session, DepositBankRequest(
            account_code=cust, amount=Decimal("100000.0000"), currency="INR",
            idempotency_key=f"seed-{cust}-{uuid.uuid4().hex[:8]}", created_by="seed-bot",
        ))
    db_session.commit()

    successes = 0
    attempts = 0
    while successes < 100 and attempts < 300:
        attempts += 1
        choice = random.choice(["deposit", "withdraw", "p2p", "fee"])
        key = f"rt-{uuid.uuid4().hex}"
        try:
            if choice == "deposit":
                process_deposit_bank(db_session, DepositBankRequest(
                    account_code=random.choice(customers),
                    amount=Decimal(str(random.randint(1, 5000))),
                    currency="INR", idempotency_key=key, created_by="rand-bot",
                ))
            elif choice == "withdraw":
                process_withdrawal(db_session, WithdrawalRequest(
                    account_code=random.choice(customers),
                    amount=Decimal(str(random.randint(1, 500))),
                    currency="INR", idempotency_key=key, created_by="rand-bot",
                ))
            elif choice == "p2p":
                sender, recipient = random.sample(customers, 2)
                process_p2p_transfer(db_session, P2PTransferRequest(
                    sender_account_code=sender, recipient_account_code=recipient,
                    amount=Decimal(str(random.randint(1, 300))),
                    fee_amount=Decimal("2.0000"),
                    currency="INR", idempotency_key=key, created_by="rand-bot",
                ))
            else:
                process_fee_deduction(db_session, FeeDeductionRequest(
                    account_code=random.choice(customers),
                    fee_amount=Decimal("5.0000"),
                    currency="INR", idempotency_key=key, created_by="rand-bot",
                ))
            db_session.commit()
            successes += 1
        except LedgerError:
            db_session.rollback()
            continue

    report = generate_trial_balance(db_session)
    assert report.is_balanced, (
        f"Trial balance discrepancy: debits={report.total_debits} "
        f"credits={report.total_credits}"
    )
    assert successes >= 100
