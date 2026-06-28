"""
src/services/transactionHandlers/reward_redemption.py

Transaction Type #19: Reward Points Redemption
Journal Pattern: Debit Rewards Liability (2030) / Credit Wallet
Key Validation: points balance / redemption rate / minimum redemption
(stubbed for Phase 1 — points ledger is out of scope; `points_redeemed` is
carried in the journal narrative/metadata for audit purposes only).
"""
from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.transaction_engine import execute_transaction
from src.services.account_service import get_or_create_customer_wallet
from src.validators.schemas import RewardRedemptionRequest

REWARDS_LIABILITY_ACCOUNT_CODE = "2030"


def _handler_factory(request: RewardRedemptionRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.currency)
        lines = [
            LineInput(
                account_code=REWARDS_LIABILITY_ACCOUNT_CODE,
                entry_type=EntryType.DEBIT,
                amount=request.redemption_amount,
                currency=request.currency,
                narrative=f"Redemption of {request.points_redeemed} reward points",
            ),
            LineInput(
                account_code=wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.redemption_amount,
                currency=request.currency,
                narrative=f"Reward points redemption ({request.points_redeemed} points)",
            ),
        ]
        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="REWARD_REDEMPTION",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_reward_redemption(db: Session, request: RewardRedemptionRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.REWARD_REDEMPTION,
        endpoint="/api/v1/reward-redemption",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
