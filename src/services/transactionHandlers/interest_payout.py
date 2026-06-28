"""
src/services/transactionHandlers/interest_payout.py

Transaction Type #9: Interest Payout (Monthly)
Journal Pattern: Debit Interest Payable (2010, gross) / Credit Wallet (net)
+ Credit TDS Payable (2020, tds_amount)
Balanced: gross = net + tds.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import InterestPayoutRequest

INTEREST_PAYABLE_ACCOUNT_CODE = "2010"
TDS_PAYABLE_ACCOUNT_CODE = "2020"


def _handler_factory(request: InterestPayoutRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)

        tds_amount = (request.gross_interest_amount * Decimal(request.tds_rate_bps) / Decimal("10000")).quantize(Decimal("0.0001"))
        net_amount = request.gross_interest_amount - tds_amount

        lines = [
            LineInput(
                account_code=INTEREST_PAYABLE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.gross_interest_amount,
                currency=request.currency,
                narrative=f"Interest payout to {request.customer_account_code}",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=net_amount,
                currency=request.currency,
                narrative="Interest payout (net of TDS)",
            ),
        ]
        if tds_amount > 0:
            lines.append(LineInput(
                account_code=TDS_PAYABLE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=tds_amount,
                currency=request.currency,
                narrative=f"TDS withheld at {request.tds_rate_bps} bps",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="INTEREST_PAYOUT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_interest_payout(db: Session, request: InterestPayoutRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.INTEREST_PAYOUT,
        endpoint="/api/v1/interest-payout",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
