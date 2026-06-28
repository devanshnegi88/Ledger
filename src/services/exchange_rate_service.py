"""
src/services/exchange_rate_service.py

Part A3.1 / A3.3, Day 6.
Rate snapshots are immutable (never UPDATEd) — a new conversion always
reads the latest valid snapshot or inserts a fresh one. Stale rates
(beyond the configured validity window) are rejected outright, addressing
Incident Card Day 6 (USD deposit converted at a 48-hour-old rate).
"""
import uuid
from uuid6 import uuid7
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from src.models.exchange_rate_snapshot import ExchangeRateSnapshot
from src.config.settings import settings
from src.utils.exceptions import StaleRateError


def get_latest_rate(db: Session, base_currency: str, quote_currency: str) -> ExchangeRateSnapshot:
    """
    Fetch the most recently captured currently-valid rate snapshot for a
    currency pair. Raises StaleRateError if none is found within the
    configured freshness window (Part A3.1 valid_from/valid_until).
    """
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(hours=settings.fx_rate_stale_threshold_hours)

    snapshot = db.execute(
        select(ExchangeRateSnapshot)
        .where(
            ExchangeRateSnapshot.base_currency == base_currency,
            ExchangeRateSnapshot.quote_currency == quote_currency,
            ExchangeRateSnapshot.valid_from <= now,
            (ExchangeRateSnapshot.valid_until.is_(None)) | (ExchangeRateSnapshot.valid_until >= now),
        )
        .order_by(desc(ExchangeRateSnapshot.captured_at))
        .limit(1)
    ).scalar_one_or_none()

    if snapshot is None:
        raise StaleRateError(
            f"No valid exchange rate snapshot found for {base_currency}/{quote_currency}"
        )

    if snapshot.captured_at < stale_cutoff:
        raise StaleRateError(
            f"Exchange rate for {base_currency}/{quote_currency} captured at "
            f"{snapshot.captured_at.isoformat()} exceeds the "
            f"{settings.fx_rate_stale_threshold_hours}h freshness window — rejecting stale rate"
        )

    return snapshot


def record_rate_snapshot(
    db: Session,
    *,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    source: str = "INTERNAL",
    valid_for_hours: Optional[int] = None,
) -> ExchangeRateSnapshot:
    """Insert a new immutable rate snapshot (and its inverse) — never updates an existing row."""
    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(hours=valid_for_hours) if valid_for_hours else None
    inverse_rate = (Decimal("1") / rate).quantize(Decimal("0.00000001"))

    snapshot = ExchangeRateSnapshot(
        snapshot_id=uuid7(),
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        inverse_rate=inverse_rate,
        source=source,
        captured_at=now,
        valid_from=now,
        valid_until=valid_until,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def convert_amount(amount: Decimal, snapshot: ExchangeRateSnapshot) -> Decimal:
    """amount (in base_currency) -> quote_currency, using the snapshot's rate."""
    return (amount * snapshot.rate).quantize(Decimal("0.0001"))
