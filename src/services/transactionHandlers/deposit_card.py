"""
src/services/transactionHandlers/deposit_card.py

Transaction Type #2: Customer Deposit (Card)
Journal Pattern: Debit Asset (pooled Wallet) / Credit Liability (customer
wallet) + Debit Expense (Gateway Fee 5001) / Credit Liability (Merchant
Payable 2002, owed to the payment gateway).

Balanced per currency: pooled asset debit (amount) + gateway fee debit
(fee) = customer wallet credit (amount) + gateway payable credit (fee).
Key Validation: card authentication / 3DS / gateway response code
(stubbed — `card_auth_token` is recorded for audit but not verified
against a real PSP in Phase 1).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet, get_pooled_asset_account_code
from src.validators.schemas import DepositCardRequest

GATEWAY_FEE_EXPENSE_ACCOUNT_CODE = "5001"
MERCHANT_PAYABLE_ACCOUNT_CODE = "2002"


def _handler_factory(request: DepositCardRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        customer_wallet = get_or_create_customer_wallet(db, request.account_code, request.currency)
        pooled_asset_code = get_pooled_asset_account_code(request.currency)

        lines = [
            LineInput(
                account_code=pooled_asset_code,
                entry_type=EntryType.DEBIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Pooled reserve increase from card deposit (auth {request.card_auth_token[:8]}...)",
            ),
            LineInput(
                account_code=customer_wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=request.narrative,
            ),
        ]
        if request.gateway_fee > 0:
            lines.append(LineInput(
                account_code=GATEWAY_FEE_EXPENSE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.gateway_fee,
                currency=request.currency,
                narrative="Card payment gateway fee",
            ))
            lines.append(LineInput(
                account_code=MERCHANT_PAYABLE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.gateway_fee,
                currency=request.currency,
                narrative="Payable to payment gateway",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="DEPOSIT_CARD",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_deposit_card(db: Session, request: DepositCardRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.DEPOSIT_CARD,
        endpoint="/api/v1/deposit-card",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
