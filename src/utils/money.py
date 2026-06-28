"""
src/utils/money.py — Decimal helpers for monetary arithmetic.
Anti-Pattern #1 guard: NEVER use float/double for money (Revolut Case Study #2).
"""
from decimal import Decimal, ROUND_HALF_UP

MONEY_QUANT = Decimal("0.0001")  # NUMERIC(19,4)


def to_money(value) -> Decimal:
    """Coerce any numeric-ish input to a properly quantized Decimal."""
    if isinstance(value, float):
        raise TypeError(
            "Refusing to convert float to money — pass a Decimal or string "
            "to avoid IEEE-754 precision loss (see Anti-Pattern #1)."
        )
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def is_positive(amount: Decimal) -> bool:
    return amount > Decimal("0")


def sum_money(values) -> Decimal:
    total = Decimal("0.0000")
    for v in values:
        total += to_money(v)
    return total
