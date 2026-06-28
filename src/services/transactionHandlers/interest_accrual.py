"""
src/services/transactionHandlers/interest_accrual.py

Transaction Type #8: Interest Accrual (Daily)
Journal Pattern: Debit Interest Expense (5003) / Credit Interest Payable (2010)
Key Validation: correct day-count convention; rate lookup; minimum balance
(rate/day-count logic lives in the scheduler job that computes
`interest_amount` before calling this handler — this handler only posts
the resulting journal entry).

No customer wallet is touched here — interest is recognised as a liability
(Interest Payable) and only paid out to the customer's wallet later via
Interest Payout (#9).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.validators.schemas import InterestAccrualRequest

INTEREST_EXPENSE_ACCOUNT_CODE = "5003"
INTEREST_PAYABLE_ACCOUNT_CODE = "2010"


def _handler_factory(request: InterestAccrualRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        lines = [
            LineInput(
                account_code=INTEREST_EXPENSE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.interest_amount,
                currency=request.currency,
                narrative=f"Interest accrual for {request.customer_account_code}",
            ),
            LineInput(
                account_code=INTEREST_PAYABLE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.interest_amount,
                currency=request.currency,
                narrative=f"Interest accrual for {request.customer_account_code}",
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="INTEREST_ACCRUAL",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_interest_accrual(db: Session, request: InterestAccrualRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.INTEREST_ACCRUAL,
        endpoint="/api/v1/interest-accrual",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
