"""
src/services/transactionHandlers/chargeback.py

Transaction Type #18: Chargeback
Journal Pattern: Debit Merchant Settlement (1010, amount+fee) / Credit
Wallet (amount) / Credit Transaction Fee Revenue (chargeback fee)
Key Validation: network dispute code / evidence / ARN matching (stubbed).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import ChargebackRequest
from src.utils.money import to_money

MERCHANT_SETTLEMENT_PENDING_CODE = "1010"
FEE_REVENUE_ACCOUNT_CODE = "4001"


def _handler_factory(request: ChargebackRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        total_debit_to_merchant = to_money(request.amount) + to_money(request.chargeback_fee)

        lines = [
            LineInput(
                account_code=MERCHANT_SETTLEMENT_PENDING_CODE,
                entry_type=EntryType.DEBIT,
                amount=total_debit_to_merchant,
                currency=request.currency,
                narrative=f"Chargeback against {request.merchant_code} ({request.network_dispute_code})",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.amount,
                currency=request.currency,
                narrative=f"Chargeback credit ({request.network_dispute_code})",
            ),
        ]
        if request.chargeback_fee > 0:
            lines.append(LineInput(
                account_code=FEE_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.chargeback_fee,
                currency=request.currency,
                narrative="Chargeback processing fee",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="CHARGEBACK",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_chargeback(db: Session, request: ChargebackRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.CHARGEBACK,
        endpoint="/api/v1/chargeback",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
