"""
src/services/transactionHandlers/p2p_transfer.py

Transaction Type #4: P2P Transfer
Journal Pattern: Debit Sender Wallet (amount+fee) / Credit Recipient Wallet
(amount) / Credit Transaction Fee Revenue (fee).

Both wallets are Liability sub-accounts (see account_service.py), so this
is a pure liability-to-liability movement plus a revenue recognition —
no pooled Asset account is touched (the bank's total reserve cash doesn't
change in a P2P transfer, only which customer the liability is owed to).

Balance check:
  Total debits  = amount + fee   (sender wallet decreases — DEBIT, since
                  Liability normal balance is CREDIT, a decrease is a DEBIT)
  Total credits = amount (recipient) + fee (revenue) = amount + fee  ✓ balanced
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_accounts_for_update_ordered
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import P2PTransferRequest
from src.utils.exceptions import InsufficientBalanceError
from src.utils.money import to_money

FEE_REVENUE_ACCOUNT_CODE = "4001"


def _handler_factory(request: P2PTransferRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        sender_wallet = get_or_create_customer_wallet(db, request.sender_account_code, request.currency)
        recipient_wallet = get_or_create_customer_wallet(db, request.recipient_account_code, request.currency)

        # Deterministic lock ordering prevents deadlocks vs a concurrent
        # reverse-direction transfer (Part A4.3 / Day 7).
        lock_accounts_for_update_ordered(db, [sender_wallet.id, recipient_wallet.id])

        total_debit_to_sender = to_money(request.amount) + to_money(request.fee_amount)
        sender_balance = get_cached_balance(db, sender_wallet.id)
        if sender_balance < total_debit_to_sender:
            raise InsufficientBalanceError(
                f"Sender balance of {request.currency} {sender_balance} is insufficient "
                f"for transfer of {request.currency} {request.amount} plus fee {request.fee_amount}"
            )

        lines = [
            LineInput(
                account_code=sender_wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=total_debit_to_sender,
                currency=request.currency,
                narrative=f"P2P transfer to {request.recipient_account_code} incl. fee",
            ),
            LineInput(
                account_code=recipient_wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"P2P transfer from {request.sender_account_code}",
            ),
        ]
        if request.fee_amount > 0:
            lines.append(
                LineInput(
                    account_code=FEE_REVENUE_ACCOUNT_CODE,
                    entry_type=EntryType.CREDIT,
                    amount=request.fee_amount,
                    currency=request.currency,
                    narrative="P2P transfer fee",
                )
            )

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="P2P_TRANSFER",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_p2p_transfer(db: Session, request: P2PTransferRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.P2P_TRANSFER,
        endpoint="/api/v1/transfer",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
