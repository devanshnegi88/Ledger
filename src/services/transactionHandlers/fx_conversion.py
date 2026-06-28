"""
src/services/transactionHandlers/fx_conversion.py

Transaction Type #15: FX Conversion
Journal Pattern (Part A3.2): Source wallet, FX Holding (source ccy),
FX Holding (target ccy), Target wallet, FX Revenue.

Balanced PER CURRENCY (see journal_entry_service._assert_balanced):
  Source currency leg:  Debit customer wallet (source) = Credit FX Holding (source)
  Target currency leg:  Debit FX Holding (target) = Credit customer wallet (target) + Credit FX Revenue

Key Validation: rate snapshot must be valid/fresh (Incident Day 6).
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from src.models.transaction import Transaction, TransactionType
from src.models.ledger_entry import EntryType
from src.services.journal_entry_service import create_journal_entry, LineInput
from src.services.balance_service import get_cached_balance
from src.services.transaction_engine import execute_transaction
from src.services.concurrency_control import lock_account_for_update
from src.services.account_service import get_or_create_customer_wallet, get_or_create_fx_holding_account
from src.services.exchange_rate_service import get_latest_rate, convert_amount
from src.validators.schemas import FXConversionRequest
from src.utils.exceptions import InsufficientBalanceError

FX_REVENUE_ACCOUNT_CODE = "4003"


def _handler_factory(request: FXConversionRequest):
    def handler(db: Session, transaction: Transaction) -> None:
        source_wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.source_currency)
        target_wallet = get_or_create_customer_wallet(db, request.customer_account_code, request.target_currency)
        source_holding = get_or_create_fx_holding_account(db, request.source_currency)
        target_holding = get_or_create_fx_holding_account(db, request.target_currency)

        lock_account_for_update(db, source_wallet.id)

        balance = get_cached_balance(db, source_wallet.id)
        if balance < request.source_amount:
            raise InsufficientBalanceError(
                f"Customer balance of {request.source_currency} {balance} is insufficient "
                f"for FX conversion of {request.source_currency} {request.source_amount}"
            )

        rate_snapshot = get_latest_rate(db, request.source_currency, request.target_currency)
        gross_target_amount = convert_amount(request.source_amount, rate_snapshot)
        markup = (gross_target_amount * Decimal(request.fx_markup_bps) / Decimal("10000")).quantize(Decimal("0.0001"))
        net_target_amount = gross_target_amount - markup

        lines = [
            # Source-currency leg — balanced within source_currency.
            LineInput(
                account_code=source_wallet.account_code,
                entry_type=EntryType.DEBIT,
                amount=request.source_amount,
                currency=request.source_currency,
                narrative=f"FX conversion {request.source_currency}->{request.target_currency}",
            ),
            LineInput(
                account_code=source_holding.account_code,
                entry_type=EntryType.CREDIT,
                amount=request.source_amount,
                currency=request.source_currency,
                narrative=f"FX holding intake ({request.source_currency})",
            ),
            # Target-currency leg — balanced within target_currency.
            LineInput(
                account_code=target_holding.account_code,
                entry_type=EntryType.DEBIT,
                amount=gross_target_amount,
                currency=request.target_currency,
                narrative=f"FX holding release ({request.target_currency}), rate snapshot {rate_snapshot.snapshot_id}",
            ),
            LineInput(
                account_code=target_wallet.account_code,
                entry_type=EntryType.CREDIT,
                amount=net_target_amount,
                currency=request.target_currency,
                narrative=f"FX conversion proceeds {request.source_currency}->{request.target_currency}",
            ),
            LineInput(
                account_code=FX_REVENUE_ACCOUNT_CODE,
                entry_type=EntryType.CREDIT,
                amount=markup,
                currency=request.target_currency,
                narrative=f"FX markup revenue ({request.fx_markup_bps} bps)",
            ),
        ]

        create_journal_entry(
            db,
            transaction=transaction,
            lines=lines,
            reference_type="FX_CONVERSION",
            reference_id=transaction.id,
            created_by=request.created_by,
            narrative=request.narrative,
        )
    return handler


def process_fx_conversion(db: Session, request: FXConversionRequest) -> Transaction:
    return execute_transaction(
        db=db,
        transaction_type=TransactionType.FX_CONVERSION,
        endpoint="/api/v1/fx",
        user_id=request.created_by,
        idempotency_key=request.idempotency_key,
        request_payload=request.model_dump(mode="json"),
        handler=_handler_factory(request),
    )
