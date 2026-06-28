"""
src/routes/transactions.py
"""
from fastapi import APIRouter, status

from src.validators.schemas import (
    DepositBankRequest, WithdrawalRequest, P2PTransferRequest, FeeDeductionRequest,
    MerchantQRPaymentRequest, MerchantOnlinePaymentRequest, BillPaymentRequest, InterestAccrualRequest,
    FXConversionRequest, FullReversalRequest, PartialRefundRequest,
    InterestPayoutRequest, CashbackCreditRequest, PromotionalCreditRequest, LoanDisbursementRequest,
    LoanEMIRequest, ChargebackRequest, RewardRedemptionRequest, AccountClosureSweepRequest,
    DepositCardRequest,
)
from src.controllers.transaction_controller import (
    handle_deposit, handle_withdrawal, handle_p2p_transfer, handle_fee_deduction,
    handle_merchant_qr_payment, handle_merchant_online_payment, handle_bill_payment,
    handle_interest_accrual, handle_fx_conversion, handle_full_reversal, handle_partial_refund,
    handle_interest_payout, handle_cashback_credit, handle_promotional_credit, handle_loan_disbursement,
    handle_loan_emi, handle_chargeback, handle_reward_redemption, handle_account_closure_sweep,
    handle_deposit_card,
)

router = APIRouter(tags=["transactions"])


@router.post("/api/v1/deposit", status_code=status.HTTP_201_CREATED)
def deposit(request: DepositBankRequest):
    return handle_deposit(request)


@router.post("/api/v1/withdraw", status_code=status.HTTP_201_CREATED)
def withdraw(request: WithdrawalRequest):
    return handle_withdrawal(request)


@router.post("/api/v1/transfer", status_code=status.HTTP_201_CREATED)
def transfer(request: P2PTransferRequest):
    return handle_p2p_transfer(request)


@router.post("/api/v1/fee-deduction", status_code=status.HTTP_201_CREATED)
def fee_deduction(request: FeeDeductionRequest):
    return handle_fee_deduction(request)


@router.post("/api/v1/merchant-payment/qr", status_code=status.HTTP_201_CREATED)
def merchant_payment_qr(request: MerchantQRPaymentRequest):
    return handle_merchant_qr_payment(request)


@router.post("/api/v1/merchant-payment/online", status_code=status.HTTP_201_CREATED)
def merchant_payment_online(request: MerchantOnlinePaymentRequest):
    return handle_merchant_online_payment(request)


@router.post("/api/v1/bill-payment", status_code=status.HTTP_201_CREATED)
def bill_payment(request: BillPaymentRequest):
    return handle_bill_payment(request)


@router.post("/api/v1/interest-accrual", status_code=status.HTTP_201_CREATED)
def interest_accrual(request: InterestAccrualRequest):
    return handle_interest_accrual(request)


@router.post("/api/v1/fx", status_code=status.HTTP_201_CREATED)
def fx_conversion(request: FXConversionRequest):
    return handle_fx_conversion(request)


@router.post("/api/v1/reversal", status_code=status.HTTP_201_CREATED)
def reversal(request: FullReversalRequest):
    return handle_full_reversal(request)


@router.post("/api/v1/refund", status_code=status.HTTP_201_CREATED)
def refund(request: PartialRefundRequest):
    return handle_partial_refund(request)


@router.post("/api/v1/interest-payout", status_code=status.HTTP_201_CREATED)
def interest_payout(request: InterestPayoutRequest):
    return handle_interest_payout(request)


@router.post("/api/v1/cashback-credit", status_code=status.HTTP_201_CREATED)
def cashback_credit(request: CashbackCreditRequest):
    return handle_cashback_credit(request)


@router.post("/api/v1/promotional-credit", status_code=status.HTTP_201_CREATED)
def promotional_credit(request: PromotionalCreditRequest):
    return handle_promotional_credit(request)


@router.post("/api/v1/loan-disbursement", status_code=status.HTTP_201_CREATED)
def loan_disbursement(request: LoanDisbursementRequest):
    return handle_loan_disbursement(request)


@router.post("/api/v1/loan-emi", status_code=status.HTTP_201_CREATED)
def loan_emi(request: LoanEMIRequest):
    return handle_loan_emi(request)


@router.post("/api/v1/chargeback", status_code=status.HTTP_201_CREATED)
def chargeback(request: ChargebackRequest):
    return handle_chargeback(request)


@router.post("/api/v1/reward-redemption", status_code=status.HTTP_201_CREATED)
def reward_redemption(request: RewardRedemptionRequest):
    return handle_reward_redemption(request)


@router.post("/api/v1/account-closure", status_code=status.HTTP_201_CREATED)
def account_closure(request: AccountClosureSweepRequest):
    return handle_account_closure_sweep(request)


@router.post("/api/v1/deposit-card", status_code=status.HTTP_201_CREATED)
def deposit_card(request: DepositCardRequest):
    return handle_deposit_card(request)
