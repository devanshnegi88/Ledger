"""
src/validators/schemas.py — Pydantic v2 request/response schemas.
"""
from decimal import Decimal
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


class JournalLineInput(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=10)
    entry_type: Literal["DEBIT", "CREDIT"]
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    narrative: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def reject_float(cls, v):
        if isinstance(v, float):
            raise ValueError("amount must be provided as a string or Decimal, never float")
        return v


class DepositBankRequest(BaseModel):
    account_code: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Customer deposit via bank transfer"


class WithdrawalRequest(BaseModel):
    account_code: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Customer withdrawal via bank transfer"


class P2PTransferRequest(BaseModel):
    sender_account_code: str
    recipient_account_code: str
    amount: Decimal = Field(..., gt=0)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "P2P transfer"


class FeeDeductionRequest(BaseModel):
    account_code: str
    fee_amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Monthly maintenance fee"


class MerchantQRPaymentRequest(BaseModel):
    customer_account_code: str
    merchant_code: str
    amount: Decimal = Field(..., gt=0)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Merchant QR payment"


class MerchantOnlinePaymentRequest(BaseModel):
    customer_account_code: str
    merchant_code: str
    amount: Decimal = Field(..., gt=0)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    gateway_session_id: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Merchant online payment"


class BillPaymentRequest(BaseModel):
    customer_account_code: str
    biller_code: str
    amount: Decimal = Field(..., gt=0)
    convenience_fee: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Bill payment"


class InterestAccrualRequest(BaseModel):
    customer_account_code: str
    interest_amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str = "system-scheduler"
    narrative: Optional[str] = "Daily interest accrual"


class FXConversionRequest(BaseModel):
    customer_account_code: str
    source_currency: str = Field(..., min_length=3, max_length=3)
    target_currency: str = Field(..., min_length=3, max_length=3)
    source_amount: Decimal = Field(..., gt=0)
    fx_markup_bps: int = Field(default=50, ge=0, description="FX markup in basis points (50 = 0.5%)")
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "FX conversion"


class FullReversalRequest(BaseModel):
    original_transaction_id: str
    reason: str
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str


class PartialRefundRequest(BaseModel):
    original_transaction_id: str
    refund_amount: Decimal = Field(..., gt=0)
    fee_refund_policy: Literal["PROPORTIONAL", "FULL", "NONE"] = "PROPORTIONAL"
    reason: str
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str


class InterestPayoutRequest(BaseModel):
    customer_account_code: str
    gross_interest_amount: Decimal = Field(..., gt=0)
    tds_rate_bps: int = Field(default=1000, ge=0, le=10000, description="TDS in basis points (1000 = 10%)")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str = "system-scheduler"
    narrative: Optional[str] = "Monthly interest payout"


class CashbackCreditRequest(BaseModel):
    customer_account_code: str
    amount: Decimal = Field(..., gt=0)
    campaign_code: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Cashback credit"


class PromotionalCreditRequest(BaseModel):
    customer_account_code: str
    amount: Decimal = Field(..., gt=0)
    promo_code: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Promotional credit"


class LoanDisbursementRequest(BaseModel):
    customer_account_code: str
    principal_amount: Decimal = Field(..., gt=0)
    processing_fee: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Loan disbursement"


class LoanEMIRequest(BaseModel):
    customer_account_code: str
    principal_component: Decimal = Field(..., ge=0)
    interest_component: Decimal = Field(..., ge=0)
    penalty_component: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Loan EMI payment"


class ChargebackRequest(BaseModel):
    customer_account_code: str
    merchant_code: str
    amount: Decimal = Field(..., gt=0)
    chargeback_fee: Decimal = Field(default=Decimal("0"), ge=0)
    network_dispute_code: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Chargeback"


class RewardRedemptionRequest(BaseModel):
    customer_account_code: str
    redemption_amount: Decimal = Field(..., gt=0)
    points_redeemed: int = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Reward points redemption"


class AccountClosureSweepRequest(BaseModel):
    customer_account_code: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Account closure sweep"


class JournalEntryResponse(BaseModel):
    journal_id: str
    journal_reference: str
    transaction_id: str
    status: str
    entries: List[dict]


class DepositCardRequest(BaseModel):
    account_code: str
    amount: Decimal = Field(..., gt=0)
    gateway_fee: Decimal = Field(default=Decimal("0"), ge=0)
    card_auth_token: str
    currency: str = Field(default="INR", min_length=3, max_length=3)
    idempotency_key: str = Field(..., min_length=8, max_length=128)
    created_by: str
    narrative: Optional[str] = "Customer deposit via card"
