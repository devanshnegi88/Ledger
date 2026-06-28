"""
src/services/transactionHandlers/account_closure_sweep.py

Transaction Type #20: Account Closure Sweep
Journal Pattern: Debit Wallet (full remaining balance) / Credit pooled
Asset (bank pays out remaining cash) — mirrors Withdrawal (#3) for the
full balance, then marks the wallet inactive so no further entries can be
posted against it.

Phase 1 scope: sweeps the wallet balance only. Settling pending refunds,
redeeming outstanding reward points, and closing active loans first
(Scenario 4 in the spec) are multi-step orchestrations layered on top of
this primitive in a later phase — this handler is the final, atomic
"zero out and pay" step once those pre-conditions are satisfied.
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet, get_pooled_asset_account_code
from src.validators.schemas import AccountClosureSweepRequest

POOLED_ASSET_BY_CURRENCY_FALLBACK = get_pooled_asset_account_code


def _handler_factory(request: AccountClosureSweepRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lock_account_for_update(db, wallet.id)

        remaining_balance = get_cached_balance(db, wallet.id)
        pooled_asset_code = get_pooled_asset_account_code(request.currency)

        if remaining_balance > 0:
            lines = [
                LineInput(
                    account_code=wallet.account_code,
                    entry_type=EntryType.DEBIT,
                    amount=remaining_balance,
                    currency=request.currency,
                    narrative="Account closure sweep — final balance payout",
                ),
                LineInput(
                    account_code=pooled_asset_code,
                    entry_type=EntryType.CREDIT,
                    amount=remaining_balance,
                    currency=request.currency,
                    narrative="Account closure sweep — pooled reserve decrease",
                ),
            ]
            create_journal_entry(
                db,
                transaction=transaction,
                lines=lines,
                reference_type="ACCOUNT_CLOSURE_SWEEP",
                reference_id=transaction.id,
                created_by=request.created_by,
                narrative=request.narrative,
            )

        wallet.is_active = False
        db.add(wallet)
    return handler


def process_account_closure_sweep(db: Session, request: AccountClosureSweepRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.ACCOUNT_CLOSURE_SWEEP,
        endpoint="/api/v1/account-closure",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
