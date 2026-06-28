"""
Hash chaining utility (Part A2.3 / A10.4).

hash = SHA256(canonical_json(entry_fields) + previous_hash)

The canonical representation MUST be deterministic: same field order,
ISO-8601 timestamps, string-formatted Decimal amounts (never float).
"""
import hashlib
import json
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, Optional


def _default_serializer(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")  # exact decimal string, never float repr
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def canonicalize(entry_fields: Dict[str, Any]) -> str:
    """Deterministic JSON serialisation for hashing."""
    return json.dumps(entry_fields, sort_keys=True, default=_default_serializer)


def compute_entry_hash(entry_fields: Dict[str, Any], previous_hash: Optional[str]) -> str:
    """
    Compute SHA-256 hash of (canonical entry data + previous hash).
    The genesis entry (first in the chain) uses previous_hash = "0" * 64.
    """
    prev = previous_hash or ("0" * 64)
    payload = canonicalize(entry_fields) + prev
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_chain_link(entry_fields: Dict[str, Any], previous_hash: Optional[str], stored_hash: str) -> bool:
    """Recompute the hash and compare against the stored value."""
    return compute_entry_hash(entry_fields, previous_hash) == stored_hash


def entry_fields_for_hash(entry) -> Dict[str, Any]:
    """
    Extract the canonical, hashable fields from a LedgerEntry ORM instance.
    Excludes mutable/derived fields (hash, previous_hash themselves).
    """
    return {
        "entry_id": str(entry.entry_id),
        "journal_id": str(entry.journal_id),
        "account_id": str(entry.account_id),
        "entry_type": entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type,
        "amount": entry.amount,
        "currency": entry.currency,
        "effective_date": entry.effective_date,
        "created_by": entry.created_by,
        "reference_type": entry.reference_type,
        "reference_id": str(entry.reference_id) if entry.reference_id else None,
        "narrative": entry.narrative,
    }
