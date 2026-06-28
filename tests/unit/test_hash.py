"""
tests/unit/hash.test — pytest module verifying hash chain integrity.
(Named per spec convention; pytest discovers test_*.py / *_test.py — see conftest)
"""
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from src.utils.hash import compute_entry_hash, verify_chain_link, canonicalize


def sample_fields(amount="1000.0000"):
    return {
        "entry_id": str(uuid.uuid4()),
        "journal_id": str(uuid.uuid4()),
        "account_id": str(uuid.uuid4()),
        "entry_type": "DEBIT",
        "amount": Decimal(amount),
        "currency": "INR",
        "effective_date": datetime(2026, 6, 20, tzinfo=timezone.utc),
        "created_by": "system",
        "reference_type": "DEPOSIT",
        "reference_id": None,
        "narrative": "Test deposit",
    }


def test_genesis_hash_uses_zero_previous():
    fields = sample_fields()
    h1 = compute_entry_hash(fields, previous_hash=None)
    h2 = compute_entry_hash(fields, previous_hash="0" * 64)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_changes_if_amount_changes():
    fields_a = sample_fields("1000.0000")
    fields_b = sample_fields("1000.0001")
    h_a = compute_entry_hash(fields_a, previous_hash="0" * 64)
    h_b = compute_entry_hash(fields_b, previous_hash="0" * 64)
    assert h_a != h_b


def test_chain_link_verification_succeeds_for_correct_chain():
    fields = sample_fields()
    prev_hash = "a" * 64
    h = compute_entry_hash(fields, prev_hash)
    assert verify_chain_link(fields, prev_hash, h) is True


def test_chain_link_verification_fails_when_tampered():
    fields = sample_fields()
    prev_hash = "a" * 64
    h = compute_entry_hash(fields, prev_hash)

    tampered_fields = dict(fields)
    tampered_fields["amount"] = Decimal("9999.9999")  # simulate tampering

    assert verify_chain_link(tampered_fields, prev_hash, h) is False


def test_canonicalize_is_deterministic_regardless_of_key_order():
    fields = sample_fields()
    shuffled = {k: fields[k] for k in reversed(list(fields.keys()))}
    assert canonicalize(fields) == canonicalize(shuffled)


def test_float_amounts_never_used_in_hash_payload():
    """Guards against Anti-Pattern #1 (Common Mistakes Catalogue):
    money must always serialise as exact decimal strings, never float repr."""
    fields = sample_fields("0.1")
    payload = canonicalize(fields)
    assert '"0.1"' in payload
    assert "0.1000000000000000055511151231257827" not in payload  # IEEE754 float repr of 0.1
