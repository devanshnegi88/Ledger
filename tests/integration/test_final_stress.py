"""
tests/integration/test_final_stress.py — Day 15

The final acceptance test: 1,000 randomised transactions across all 20
transaction types, with a final trial balance and hash-chain verification.
This reuses the Day 9 generator (test_all_transaction_types.run_one logic)
scaled to 1,000 successes, plus a hash-chain integrity check at the end —
"the moment of truth."
"""
from decimal import Decimal
import uuid
import random

import pytest

from src.validators.schemas import DepositBankRequest
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.trial_balance_service import generate_trial_balance
from src.services.audit_service import verify_hash_chain
from src.utils.exceptions import LedgerError


@pytest.mark.slow
def test_1000_random_transactions_final_trial_balance_and_hash_chain(db_session):
    customers = [f"cust-final-{i:03d}" for i in range(20)]
    for cust in customers:
        process_deposit_bank(db_session, DepositBankRequest(
            account_code=cust, amount=Decimal("500000.0000"), currency="INR",
            idempotency_key=f"final-seed-{uuid.uuid4().hex}", created_by="seed-bot",
        ))
        process_deposit_bank(db_session, DepositBankRequest(
            account_code=cust, amount=Decimal("10000.0000"), currency="USD",
            idempotency_key=f"final-seed-{uuid.uuid4().hex}", created_by="seed-bot",
        ))
    db_session.commit()

    from tests.integration.test_all_transaction_types import _rand_amount
    from src.validators.schemas import (
        DepositCardRequest, WithdrawalRequest, P2PTransferRequest, MerchantQRPaymentRequest,
        MerchantOnlinePaymentRequest, BillPaymentRequest, InterestAccrualRequest, InterestPayoutRequest,
        FeeDeductionRequest, CashbackCreditRequest, PromotionalCreditRequest, LoanDisbursementRequest,
        LoanEMIRequest, FXConversionRequest, ChargebackRequest, RewardRedemptionRequest,
        AccountClosureSweepRequest, FullReversalRequest, PartialRefundRequest,
    )
    from src.services.transactionHandlers.deposit_card import process_deposit_card
    from src.services.transactionHandlers.withdrawal import process_withdrawal
    from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
    from src.services.transactionHandlers.merchant_payment_qr import process_merchant_qr_payment
    from src.services.transactionHandlers.merchant_payment_online import process_merchant_online_payment
    from src.services.transactionHandlers.bill_payment import process_bill_payment
    from src.services.transactionHandlers.interest_accrual import process_interest_accrual
    from src.services.transactionHandlers.interest_payout import process_interest_payout
    from src.services.transactionHandlers.fee_deduction import process_fee_deduction
    from src.services.transactionHandlers.cashback_credit import process_cashback_credit
    from src.services.transactionHandlers.promotional_credit import process_promotional_credit
    from src.services.transactionHandlers.loan_disbursement import process_loan_disbursement
    from src.services.transactionHandlers.loan_emi import process_loan_emi
    from src.services.transactionHandlers.fx_conversion import process_fx_conversion
    from src.services.transactionHandlers.chargeback import process_chargeback
    from src.services.transactionHandlers.reward_redemption import process_reward_redemption
    from src.services.transactionHandlers.account_closure_sweep import process_account_closure_sweep
    from src.services.reversal_service import process_full_reversal, process_partial_refund

    key = lambda: f"k-{uuid.uuid4().hex}"  # noqa: E731

    def run_one():
        c = random.choice(customers)
        c2 = random.choice([x for x in customers if x != c])
        choice = random.randint(1, 20)
        if choice == 1:
            process_deposit_bank(db_session, DepositBankRequest(
                account_code=c, amount=_rand_amount(), currency="INR", idempotency_key=key(), created_by=c))
        elif choice == 2:
            process_deposit_card(db_session, DepositCardRequest(
                account_code=c, amount=_rand_amount(), gateway_fee=Decimal("5"),
                card_auth_token="tok_" + uuid.uuid4().hex, idempotency_key=key(), created_by=c))
        elif choice == 3:
            process_withdrawal(db_session, WithdrawalRequest(
                account_code=c, amount=_rand_amount(1, 300), idempotency_key=key(), created_by=c))
        elif choice == 4:
            process_p2p_transfer(db_session, P2PTransferRequest(
                sender_account_code=c, recipient_account_code=c2, amount=_rand_amount(1, 300),
                fee_amount=Decimal("2"), idempotency_key=key(), created_by=c))
        elif choice == 5:
            process_merchant_qr_payment(db_session, MerchantQRPaymentRequest(
                customer_account_code=c, merchant_code="MER001", amount=_rand_amount(1, 200),
                fee_amount=Decimal("1"), tax_amount=Decimal("0.5"), idempotency_key=key(), created_by=c))
        elif choice == 6:
            process_merchant_online_payment(db_session, MerchantOnlinePaymentRequest(
                customer_account_code=c, merchant_code="MER002", amount=_rand_amount(1, 200),
                fee_amount=Decimal("1"), tax_amount=Decimal("0.5"),
                gateway_session_id=uuid.uuid4().hex, idempotency_key=key(), created_by=c))
        elif choice == 7:
            process_bill_payment(db_session, BillPaymentRequest(
                customer_account_code=c, biller_code="BILLER01", amount=_rand_amount(1, 150),
                convenience_fee=Decimal("3"), idempotency_key=key(), created_by=c))
        elif choice == 8:
            process_interest_accrual(db_session, InterestAccrualRequest(
                customer_account_code=c, interest_amount=_rand_amount(1, 20), idempotency_key=key()))
        elif choice == 9:
            process_interest_payout(db_session, InterestPayoutRequest(
                customer_account_code=c, gross_interest_amount=_rand_amount(1, 20), idempotency_key=key()))
        elif choice == 10:
            process_fee_deduction(db_session, FeeDeductionRequest(
                account_code=c, fee_amount=Decimal("5"), idempotency_key=key(), created_by=c))
        elif choice == 11:
            process_cashback_credit(db_session, CashbackCreditRequest(
                customer_account_code=c, amount=_rand_amount(1, 50), campaign_code="CB01",
                idempotency_key=key(), created_by="promo-bot"))
        elif choice == 12:
            process_promotional_credit(db_session, PromotionalCreditRequest(
                customer_account_code=c, amount=_rand_amount(1, 50), promo_code="PROMO01",
                idempotency_key=key(), created_by="promo-bot"))
        elif choice == 13:
            process_loan_disbursement(db_session, LoanDisbursementRequest(
                customer_account_code=c, principal_amount=_rand_amount(100, 1000),
                processing_fee=Decimal("10"), idempotency_key=key(), created_by="loan-bot"))
        elif choice == 14:
            process_loan_emi(db_session, LoanEMIRequest(
                customer_account_code=c, principal_component=_rand_amount(10, 100),
                interest_component=_rand_amount(1, 20), penalty_component=Decimal("0"),
                idempotency_key=key(), created_by=c))
        elif choice == 15:
            process_fx_conversion(db_session, FXConversionRequest(
                customer_account_code=c, source_currency="USD", target_currency="INR",
                source_amount=_rand_amount(1, 50), idempotency_key=key(), created_by=c))
        elif choice == 16:
            txn = process_p2p_transfer(db_session, P2PTransferRequest(
                sender_account_code=c, recipient_account_code=c2, amount=_rand_amount(1, 100),
                fee_amount=Decimal("1"), idempotency_key=key(), created_by=c))
            db_session.flush()
            process_full_reversal(db_session, FullReversalRequest(
                original_transaction_id=str(txn.id), reason="final-stress-full-refund",
                idempotency_key=key(), created_by=c))
        elif choice == 17:
            txn = process_p2p_transfer(db_session, P2PTransferRequest(
                sender_account_code=c, recipient_account_code=c2, amount=Decimal("100"),
                fee_amount=Decimal("2"), idempotency_key=key(), created_by=c))
            db_session.flush()
            process_partial_refund(db_session, PartialRefundRequest(
                original_transaction_id=str(txn.id), refund_amount=Decimal("40"),
                fee_refund_policy="PROPORTIONAL", reason="final-stress-partial-refund",
                idempotency_key=key(), created_by=c))
        elif choice == 18:
            process_chargeback(db_session, ChargebackRequest(
                customer_account_code=c, merchant_code="MER003", amount=_rand_amount(1, 100),
                chargeback_fee=Decimal("2"), network_dispute_code="DISPUTE01",
                idempotency_key=key(), created_by="ops-bot"))
        elif choice == 19:
            process_reward_redemption(db_session, RewardRedemptionRequest(
                customer_account_code=c, redemption_amount=_rand_amount(1, 30), points_redeemed=100,
                idempotency_key=key(), created_by=c))
        else:
            process_account_closure_sweep(db_session, AccountClosureSweepRequest(
                customer_account_code=c, idempotency_key=key(), created_by=c))
            process_deposit_bank(db_session, DepositBankRequest(
                account_code=c, amount=Decimal("1000.0000"), currency="INR",
                idempotency_key=key(), created_by="seed-bot"))

    successes = 0
    attempts = 0
    while successes < 1000 and attempts < 3000:
        attempts += 1
        try:
            run_one()
            db_session.commit()
            successes += 1
        except LedgerError:
            db_session.rollback()
            continue

    report = generate_trial_balance(db_session)
    assert report.is_balanced, (
        f"FINAL TRIAL BALANCE DISCREPANCY after {successes} txns: "
        f"debits={report.total_debits} credits={report.total_credits}"
    )

    chain_result = verify_hash_chain(db_session)
    assert chain_result.is_intact, f"Hash chain broken: {chain_result.break_reason}"

    assert successes >= 1000
