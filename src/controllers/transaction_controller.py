"""
src/controllers/transaction_controller.py
"""
from sqlalchemy.orm import Session

from src.config.database import db_transaction
from src.validators.schemas import (
    DepositBankRequest, WithdrawalRequest, P2PTransferRequest, FeeDeductionRequest,
    MerchantQRPaymentRequest, MerchantOnlinePaymentRequest, BillPaymentRequest, InterestAccrualRequest,
    FXConversionRequest, FullReversalRequest, PartialRefundRequest,
    InterestPayoutRequest, CashbackCreditRequest, PromotionalCreditRequest, LoanDisbursementRequest,
    LoanEMIRequest, ChargebackRequest, RewardRedemptionRequest, AccountClosureSweepRequest,
    DepositCardRequest,
)
from src.services.transactionHandlers.deposit import process_deposit_bank
from src.services.transactionHandlers.withdrawal import process_withdrawal
from src.services.transactionHandlers.p2p_transfer import process_p2p_transfer
from src.services.transactionHandlers.fee_deduction import process_fee_deduction
from src.services.transactionHandlers.merchant_payment_qr import process_merchant_qr_payment
from src.services.transactionHandlers.merchant_payment_online import process_merchant_online_payment
from src.services.transactionHandlers.bill_payment import process_bill_payment
from src.services.transactionHandlers.interest_accrual import process_interest_accrual
from src.services.transactionHandlers.fx_conversion import process_fx_conversion
from src.services.reversal_service import process_full_reversal, process_partial_refund
from src.services.transactionHandlers.interest_payout import process_interest_payout
from src.services.transactionHandlers.cashback_credit import process_cashback_credit
from src.services.transactionHandlers.promotional_credit import process_promotional_credit
from src.services.transactionHandlers.loan_disbursement import process_loan_disbursement
from src.services.transactionHandlers.loan_emi import process_loan_emi
from src.services.transactionHandlers.chargeback import process_chargeback
from src.services.transactionHandlers.reward_redemption import process_reward_redemption
from src.services.transactionHandlers.account_closure_sweep import process_account_closure_sweep
from src.services.transactionHandlers.deposit_card import process_deposit_card


def _serialize_transaction(txn) -> dict:
    return {
        "transaction_id": str(txn.id),
        "transaction_type": txn.transaction_type.value if hasattr(txn.transaction_type, "value") else txn.transaction_type,
        "status": txn.status.value if hasattr(txn.status, "value") else txn.status,
        "created_by": txn.created_by,
    }


def handle_deposit(request: DepositBankRequest) -> dict:
    with db_transaction() as db:
        txn = process_deposit_bank(db, request)
        return _serialize_transaction(txn)


def handle_withdrawal(request: WithdrawalRequest) -> dict:
    with db_transaction() as db:
        txn = process_withdrawal(db, request)
        return _serialize_transaction(txn)


def handle_p2p_transfer(request: P2PTransferRequest) -> dict:
    with db_transaction() as db:
        txn = process_p2p_transfer(db, request)
        return _serialize_transaction(txn)


def handle_fee_deduction(request: FeeDeductionRequest) -> dict:
    with db_transaction() as db:
        txn = process_fee_deduction(db, request)
        return _serialize_transaction(txn)


def handle_merchant_qr_payment(request: MerchantQRPaymentRequest) -> dict:
    with db_transaction() as db:
        txn = process_merchant_qr_payment(db, request)
        return _serialize_transaction(txn)


def handle_merchant_online_payment(request: MerchantOnlinePaymentRequest) -> dict:
    with db_transaction() as db:
        txn = process_merchant_online_payment(db, request)
        return _serialize_transaction(txn)


def handle_bill_payment(request: BillPaymentRequest) -> dict:
    with db_transaction() as db:
        txn = process_bill_payment(db, request)
        return _serialize_transaction(txn)


def handle_interest_accrual(request: InterestAccrualRequest) -> dict:
    with db_transaction() as db:
        txn = process_interest_accrual(db, request)
        return _serialize_transaction(txn)


def handle_fx_conversion(request: FXConversionRequest) -> dict:
    with db_transaction() as db:
        txn = process_fx_conversion(db, request)
        return _serialize_transaction(txn)


def handle_full_reversal(request: FullReversalRequest) -> dict:
    with db_transaction() as db:
        txn = process_full_reversal(db, request)
        return _serialize_transaction(txn)


def handle_partial_refund(request: PartialRefundRequest) -> dict:
    with db_transaction() as db:
        txn = process_partial_refund(db, request)
        return _serialize_transaction(txn)


def handle_interest_payout(request: InterestPayoutRequest) -> dict:
    with db_transaction() as db:
        txn = process_interest_payout(db, request)
        return _serialize_transaction(txn)


def handle_cashback_credit(request: CashbackCreditRequest) -> dict:
    with db_transaction() as db:
        txn = process_cashback_credit(db, request)
        return _serialize_transaction(txn)


def handle_promotional_credit(request: PromotionalCreditRequest) -> dict:
    with db_transaction() as db:
        txn = process_promotional_credit(db, request)
        return _serialize_transaction(txn)


def handle_loan_disbursement(request: LoanDisbursementRequest) -> dict:
    with db_transaction() as db:
        txn = process_loan_disbursement(db, request)
        return _serialize_transaction(txn)


def handle_loan_emi(request: LoanEMIRequest) -> dict:
    with db_transaction() as db:
        txn = process_loan_emi(db, request)
        return _serialize_transaction(txn)


def handle_chargeback(request: ChargebackRequest) -> dict:
    with db_transaction() as db:
        txn = process_chargeback(db, request)
        return _serialize_transaction(txn)


def handle_reward_redemption(request: RewardRedemptionRequest) -> dict:
    with db_transaction() as db:
        txn = process_reward_redemption(db, request)
        return _serialize_transaction(txn)


def handle_account_closure_sweep(request: AccountClosureSweepRequest) -> dict:
    with db_transaction() as db:
        txn = process_account_closure_sweep(db, request)
        return _serialize_transaction(txn)


def handle_deposit_card(request: DepositCardRequest) -> dict:
    with db_transaction() as db:
        txn = process_deposit_card(db, request)
        return _serialize_transaction(txn)
