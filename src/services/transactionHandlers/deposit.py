"""
src/services/transactionHandlers/deposit.py

Transaction Type #1: Customer Deposit (Bank Transfer)
Journal Pattern: Debit Asset (pooled Wallet 1001/1002/1003) /
                  Credit Liability (customer's wallet sub-account under 2001)

See src/services/account_service.py docstring for why customer wallets are
modelled as Liability sub-accounts rather than the pooled Asset account.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet, get_pooled_asset_account_code
from src.validators.schemas import DepositBankRequest


def _handler_factory(request: DepositBankRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        customer_wallet = get_or_create_customer_wallet(db, request.account_code, request.currency)
        pooled_asset_code = get_pooled_asset_account_code(request.currency)

        lines = [
            LineInput(
                account_code=pooled_asset_code,
                entry_type=EntryType.DEBIT,
                amount=request.amount,
                currency=request.currency,
                narrative="Pooled reserve increase from customer deposit",
            ),
            LineInput(
                account_code=customer_wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=request.narrative,
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="DEPOSIT_BANK",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_deposit_bank(db: Session, request: DepositBankRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.DEPOSIT_BANK,
        endpoint="/api/v1/deposit",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
