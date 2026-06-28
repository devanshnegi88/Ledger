"""
src/services/transactionHandlers/fee_deduction.py

Transaction Type #10: Fee Deduction (Monthly Maintenance)
Journal Pattern: Debit Wallet (Liability, decrease) / Credit Fee Revenue
Key Validation: fee schedule lookup; waiver eligibility; minimum balance
(stubbed for Phase 1 — wired to a rules engine in a later phase).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import FeeDeductionRequest
from src.utils.exceptions import InsufficientBalanceError

FEE_REVENUE_ACCOUNT_CODE = "4001"


def _handler_factory(request: FeeDeductionRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.account_code, request.currency)
        lock_account_for_update(db, wallet.id)

        current_balance = get_cached_balance(db, wallet.id)
        if current_balance < request.fee_amount:
            raise InsufficientBalanceError(
                f"Account balance of {request.currency} {current_balance} is insufficient "
                f"to deduct fee of {request.currency} {request.fee_amount}"
            )

        lines = [
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=request.fee_amount,
                currency=request.currency,
                narrative=request.narrative,
            ),
            LineInput(
                account_code=FEE_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.fee_amount,
                currency=request.currency,
                narrative=request.narrative,
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="FEE_DEDUCTION",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_fee_deduction(db: Session, request: FeeDeductionRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.FEE_DEDUCTION,
        endpoint="/api/v1/fee-deduction",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
