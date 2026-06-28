"""
src/services/transactionHandlers/cashback_credit.py

Transaction Type #11: Cashback Credit
Journal Pattern: Debit Cashback Expense (5002) / Credit Wallet
Key Validation: campaign active; eligibility; cap (stubbed for Phase 1).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import CashbackCreditRequest

CASHBACK_EXPENSE_ACCOUNT_CODE = "5002"


def _handler_factory(request: CashbackCreditRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lines = [
            LineInput(
                account_code=CASHBACK_EXPENSE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Cashback campaign {request.campaign_code}",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Cashback credit ({request.campaign_code})",
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="CASHBACK_CREDIT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_cashback_credit(db: Session, request: CashbackCreditRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.CASHBACK_CREDIT,
        endpoint="/api/v1/cashback-credit",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
