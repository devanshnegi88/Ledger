"""
src/services/transactionHandlers/promotional_credit.py

Transaction Type #12: Promotional Credit
Journal Pattern: Debit Marketing Expense / Credit Wallet
Key Validation: promo code valid; one-time use; expiry (stubbed).

Phase 1 simplification: reuses account 5002 (Cashback Expense, sub_type
"Marketing Expense") rather than introducing a 20th account, since both
cashback and promotional credits are marketing-expense-funded customer
incentives. Documented in docs/submission-notes.md.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import PromotionalCreditRequest

MARKETING_EXPENSE_ACCOUNT_CODE = "5002"


def _handler_factory(request: PromotionalCreditRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lines = [
            LineInput(
                account_code=MARKETING_EXPENSE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Promotional credit ({request.promo_code})",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Promotional credit ({request.promo_code})",
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="PROMOTIONAL_CREDIT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_promotional_credit(db: Session, request: PromotionalCreditRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.PROMOTIONAL_CREDIT,
        endpoint="/api/v1/promotional-credit",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
