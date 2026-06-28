"""
src/services/transactionHandlers/loan_emi.py

Transaction Type #14: Loan EMI Payment
Journal Pattern: Debit Wallet (total EMI) / Credit Principal (Loan
Receivable 1020) + Credit Interest Income (4002) + Credit Interest Income
(penalty component, reusing 4002 — see note below).
Key Validation: EMI schedule / pre-payment / penalty calc done by the
caller (e.g. a loan-servicing module) before this handler is invoked;
amounts arrive already split into principal/interest/penalty components.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import LoanEMIRequest
from src.utils.exceptions import InsufficientBalanceError

LOAN_RECEIVABLE_ACCOUNT_CODE = "1020"
INTEREST_INCOME_ACCOUNT_CODE = "4002"


def _handler_factory(request: LoanEMIRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lock_account_for_update(db, wallet.id)

        total_emi = request.principal_component + request.interest_component + request.penalty_component
        balance = get_cached_balance(db, wallet.id)
        if balance < total_emi:
            raise InsufficientBalanceError(
                f"Customer balance of {request.currency} {balance} is insufficient "
                f"for EMI payment of {request.currency} {total_emi}"
            )

        lines = [
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=total_emi,
                currency=request.currency,
                narrative="Loan EMI payment",
            ),
        ]
        if request.principal_component > 0:
            lines.append(LineInput(
                account_code=LOAN_RECEIVABLE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.principal_component,
                currency=request.currency,
                narrative="EMI principal repayment",
            ))
        if request.interest_component > 0:
            lines.append(LineInput(
                account_code=INTEREST_INCOME_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.interest_component,
                currency=request.currency,
                narrative="EMI regular interest",
            ))
        if request.penalty_component > 0:
            lines.append(LineInput(
                account_code=INTEREST_INCOME_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=request.penalty_component,
                currency=request.currency,
                narrative="EMI overdue penalty interest",
            ))

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="LOAN_EMI",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_loan_emi(db: Session, request: LoanEMIRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.LOAN_EMI,
        endpoint="/api/v1/loan-emi",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
