"""
src/utils/exceptions.py — domain exceptions mapped to Part A10.1 error categories.
"""


class LedgerError(Exception):
    """Base class for all domain-level ledger errors."""
    http_status = 500
    error_type = "INTERNAL_ERROR"
    error_code = "LEDGER_5000"


class UnbalancedJournalError(LedgerError):
    http_status = 422
    error_type = "UNBALANCED_JOURNAL"
    error_code = "TXN_4000"


class InsufficientBalanceError(LedgerError):
    http_status = 422
    error_type = "INSUFFICIENT_BALANCE"
    error_code = "TXN_4001"


class AccountNotFoundError(LedgerError):
    http_status = 404
    error_type = "ACCOUNT_NOT_FOUND"
    error_code = "TXN_4040"


class IdempotencyConflictError(LedgerError):
    http_status = 409
    error_type = "IDEMPOTENCY_CONFLICT"
    error_code = "TXN_4090"


class StaleRateError(LedgerError):
    http_status = 422
    error_type = "STALE_EXCHANGE_RATE"
    error_code = "TXN_4002"


class RefundExceedsOriginalError(LedgerError):
    http_status = 422
    error_type = "REFUND_EXCEEDS_ORIGINAL"
    error_code = "TXN_4003"


class InvalidStateTransitionError(LedgerError):
    http_status = 409
    error_type = "INVALID_STATE_TRANSITION"
    error_code = "TXN_4091"


class HashChainIntegrityError(LedgerError):
    http_status = 500
    error_type = "HASH_CHAIN_BROKEN"
    error_code = "LEDGER_5001"
