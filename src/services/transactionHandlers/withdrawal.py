"""
src/services/transactionHandlers/withdrawal.py

Transaction Type #3: Customer Withdrawal (Bank Transfer)
Journal Pattern: Debit Liability (customer wallet) / Credit Asset (pooled wallet)
Key Validation: balance check (pessimistic lock prevents double-spend, Part A4.3).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet, get_pooled_asset_account_code
from src.validators.schemas import WithdrawalRequest
from src.utils.exceptions import InsufficientBalanceError


def _handler_factory(request: WithdrawalRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        customer_wallet = get_or_create_customer_wallet(db, request.account_code, request.currency)
        pooled_asset_code = get_pooled_asset_account_code(request.currency)

        # Pessimistic lock (Part A4.3) — prevents the TOCTOU race condition
        # (Anti-Pattern #6 / Case Study #4) where two concurrent withdrawals
        # both read a sufficient balance before either commits.
        lock_account_for_update(db, customer_wallet.id)

        current_balance = get_cached_balance(db, customer_wallet.id)
        if current_balance < request.amount:
            raise InsufficientBalanceError(
                f"Account balance of {request.currency} {current_balance} is "
                f"insufficient for withdrawal of {request.currency} {request.amount}"
            )

        lines = [
            LineInput(
                account_code=customer_wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=request.amount,
                currency=request.currency,
                narrative=request.narrative,
            ),
            LineInput(
                account_code=pooled_asset_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative="Pooled reserve decrease from customer withdrawal",
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="WITHDRAWAL",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_withdrawal(db: Session, request: WithdrawalRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.WITHDRAWAL,
        endpoint="/api/v1/withdraw",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
