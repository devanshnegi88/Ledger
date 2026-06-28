"""
src/services/transactionHandlers/merchant_payment_online.py

Transaction Type #6: Merchant Payment (Online)
Same journal pattern as QR (#5) with an added gateway session reference.
Key Validation: payment page session; timeout; idempotency.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import MerchantOnlinePaymentRequest
from src.utils.exceptions import InsufficientBalanceError
from src.utils.money import to_money

MERCHANT_SETTLEMENT_PENDING_CODE = "1010"
FEE_REVENUE_ACCOUNT_CODE = "4001"
TCS_LIABILITY_ACCOUNT_CODE = "2020"


def _handler_factory(request: MerchantOnlinePaymentRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        customer_wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lock_account_for_update(db, customer_wallet.id)

        total_debit = to_money(request.amount) + to_money(request.fee_amount) + to_money(request.tax_amount)
        balance = get_cached_balance(db, customer_wallet.id)
        if balance < total_debit:
            raise InsufficientBalanceError(
                f"Customer balance of {request.currency} {balance} is insufficient "
                f"for merchant payment of {request.currency} {total_debit} (incl. fee+tax)"
            )

        lines = [
            LineInput(
                account_code=customer_wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=total_debit,
                currency=request.currency,
                narrative=f"Merchant online payment to {request.merchant_code} (session {request.gateway_session_id})",
            ),
            LineInput(
                account_code=MERCHANT_SETTLEMENT_PENDING_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Merchant settlement pending: {request.merchant_code}",
            ),
        ]
        if request.fee_amount > 0:
            lines.append(LineInput(
                account_code=FEE_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.fee_amount,
                currency=request.currency,
                narrative="Merchant online transaction fee",
            ))
        if request.tax_amount > 0:
            lines.append(LineInput(
                account_code=TCS_LIABILITY_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.tax_amount,
                currency=request.currency,
                narrative="Tax collected at source",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="MERCHANT_ONLINE_PAYMENT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_merchant_online_payment(db: Session, request: MerchantOnlinePaymentRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.MERCHANT_ONLINE_PAYMENT,
        endpoint="/api/v1/merchant-payment/online",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
