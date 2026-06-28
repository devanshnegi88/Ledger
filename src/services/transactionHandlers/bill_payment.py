"""
src/services/transactionHandlers/bill_payment.py

Transaction Type #7: Bill Payment
Journal Pattern: Debit Customer Wallet / Credit Biller Settlement +
Convenience Fee Revenue.
Key Validation: biller active; bill validation; due date check (stubbed).

Note: "Biller Settlement" reuses the Merchant Settlement (Pending) account
(1010) since billers are settled through the same pending-settlement
mechanism as merchants in this Phase 1 model; a dedicated biller ledger can
be split out later without affecting customer-facing balances.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import BillPaymentRequest
from src.utils.exceptions import InsufficientBalanceError
from src.utils.money import to_money

BILLER_SETTLEMENT_PENDING_CODE = "1010"
FEE_REVENUE_ACCOUNT_CODE = "4001"


def _handler_factory(request: BillPaymentRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        customer_wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lock_account_for_update(db, customer_wallet.id)

        total_debit = to_money(request.amount) + to_money(request.convenience_fee)
        balance = get_cached_balance(db, customer_wallet.id)
        if balance < total_debit:
            raise InsufficientBalanceError(
                f"Customer balance of {request.currency} {balance} is insufficient "
                f"for bill payment of {request.currency} {total_debit} (incl. convenience fee)"
            )

        lines = [
            LineInput(
                account_code=customer_wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=total_debit,
                currency=request.currency,
                narrative=f"Bill payment to {request.biller_code}",
            ),
            LineInput(
                account_code=BILLER_SETTLEMENT_PENDING_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Biller settlement pending: {request.biller_code}",
            ),
        ]
        if request.convenience_fee > 0:
            lines.append(LineInput(
                account_code=FEE_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.convenience_fee,
                currency=request.currency,
                narrative="Bill payment convenience fee",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="BILL_PAYMENT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_bill_payment(db: Session, request: BillPaymentRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.BILL_PAYMENT,
        endpoint="/api/v1/bill-payment",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
