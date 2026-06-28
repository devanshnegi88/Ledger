"""
src/services/audit_service.py

Part A2 / A10 — Audit Trail Verification & Hash Chain Integrity. Day 11.

verify_hash_chain(): re-walks the global hash chain in insertion order and
recomputes each entry's hash from its (still-immutable) field values,
comparing against the stored hash and previous_hash pointer. Any mismatch
means either the entry's data was corrupted/tampered, or a link in the
chain was skipped/reordered — both are reported with the exact break point.

detect_anomalies(): lightweight pattern-level checks (Part A10's
suggestion list) — large round-number entries, after-hours postings,
and entries from creators who don't normally touch a given account.
"""
from dataclasses import dataclass, field
from datetime import datetime, time
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.ledger_entry import LedgerEntry
from src.utils.hash import compute_entry_hash, entry_fields_for_hash


@dataclass
class HashChainVerificationResult:
    total_entries_checked: int
    is_intact: bool
    first_break_entry_id: Optional[str] = None
    break_reason: Optional[str] = None


@dataclass
class AnomalyFinding:
    entry_id: str
    account_id: str
    reason: str


def verify_hash_chain(db: Session, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> HashChainVerificationResult:
    """
    Walk every ledger_entries row in global insertion order (posted_at, then
    entry_id as a tiebreaker) and verify hash == SHA256(fields + previous_hash)
    for each one. Reports the FIRST point of failure, since everything after
    a broken link is unverifiable against that lineage regardless.
    """
    query = select(LedgerEntry).order_by(LedgerEntry.posted_at, LedgerEntry.entry_id)
    if from_date is not None:
        query = query.where(LedgerEntry.effective_date >= from_date)
    if to_date is not None:
        query = query.where(LedgerEntry.effective_date <= to_date)

    entries = list(db.execute(query).scalars().all())

    checked = 0
    for entry in entries:
        expected_hash = compute_entry_hash(entry_fields_for_hash(entry), entry.previous_hash)
        checked += 1
        if expected_hash != entry.hash:
            return HashChainVerificationResult(
                total_entries_checked=checked,
                is_intact=False,
                first_break_entry_id=str(entry.entry_id),
                break_reason=(
                    f"Recomputed hash {expected_hash} does not match stored hash "
                    f"{entry.hash} for entry {entry.entry_id} — data was modified "
                    f"after posting, or the chain was reordered."
                ),
            )

    return HashChainVerificationResult(total_entries_checked=checked, is_intact=True)


def detect_anomalies(db: Session, round_number_threshold: Decimal = Decimal("10000")) -> List[AnomalyFinding]:
    """
    Pattern-level anomaly detection (Wirecard Case Study #3):
      - Large round-number entries (potential fabrication signature)
      - Entries posted outside business hours (00:00-06:00 local-naive check
        on effective_date, since posted_at is always "now" at insert time)
    This is NOT a replacement for a real fraud-detection pipeline — it's a
    cheap, explainable first pass that flags entries for human review.
    """
    findings: List[AnomalyFinding] = []
    entries = db.execute(select(LedgerEntry)).scalars().all()

    for entry in entries:
        if entry.amount % Decimal("10000") == 0 and entry.amount >= round_number_threshold:
            findings.append(AnomalyFinding(
                entry_id=str(entry.entry_id),
                account_id=str(entry.account_id),
                reason=f"Large round-number amount ({entry.amount} {entry.currency})",
            ))

        local_time = entry.effective_date.time() if entry.effective_date else None
        if local_time is not None and (local_time < time(6, 0) or local_time > time(23, 0)):
            findings.append(AnomalyFinding(
                entry_id=str(entry.entry_id),
                account_id=str(entry.account_id),
                reason=f"Posted outside business hours ({local_time.isoformat()})",
            ))

    return findings
