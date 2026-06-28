"""
src/services/transactionHandlers/loan_disbursement.py

Transaction Type #13: Loan Disbursement
Journal Pattern: Debit Loan Receivable (1020, full principal) / Credit
Wallet (net principal) + Credit Transaction Fee Revenue (processing fee)
Balanced: principal = net + fee.
Key Validation: credit score / sanction letter (stubbed for Phase 1).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import LoanDisbursementRequest

LOAN_RECEIVABLE_ACCOUNT_CODE = "1020"
FEE_REVENUE_ACCOUNT_CODE = "4001"


def _handler_factory(request: LoanDisbursementRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        net_principal = request.principal_amount - request.processing_fee

        lines = [
            LineInput(
                account_code=LOAN_RECEIVABLE_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.principal_amount,
                currency=request.currency,
                narrative=f"Loan disbursement to {request.customer_account_code}",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=net_principal,
                currency=request.currency,
                narrative="Loan disbursement (net of processing fee)",
            ),
        ]
        if request.processing_fee > 0:
            lines.append(LineInput(
                account_code=FEE_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.processing_fee,
                currency=request.currency,
                narrative="Loan processing fee",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="LOAN_DISBURSEMENT",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_loan_disbursement(db: Session, request: LoanDisbursementRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.LOAN_DISBURSEMENT,
        endpoint="/api/v1/loan-disbursement",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
