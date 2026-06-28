# Incident Post-Mortem: Concurrent Double-Spend Verification

**Incident Card (Day 10):** Two concurrent withdrawals on the same account
both succeeded, leaving the account with a negative INR 8,500 balance.

## Root Cause
Classic TOCTOU (time-of-check-to-time-of-use) race: both withdrawal
requests read the account balance, both observed "sufficient funds," and
both proceeded to write before either had committed — because neither
request held a lock that would force the second to wait for the first's
result.

## Design Solution Implemented (cross-referenced to Day 7)
1. **`concurrency_control.lock_account_for_update()`** acquires
   `SELECT ... FOR UPDATE` on the account row as the *first* step inside
   the withdrawal handler, before the balance check — so the second
   concurrent request blocks until the first transaction commits or rolls
   back, and re-reads the now-updated balance.
2. **Verified empirically**, not just by code review:
   `tests/load/test_concurrent_withdrawal.py` fires 50 concurrent
   withdrawal requests (each its own thread + its own DB session, to
   genuinely exercise PostgreSQL row locking) against an account with
   exactly enough balance for 20 of them, and asserts:
   - Exactly 20 succeed, exactly 30 fail with `InsufficientBalanceError`.
   - The final balance is exactly zero — never negative.
3. **Multi-account operations** (P2P transfer) use
   `lock_accounts_for_update_ordered()` with deterministic ascending-UUID
   lock ordering, verified by `tests/load/test_concurrent_p2p.py` (20
   concurrent bidirectional transfers between the same two accounts, zero
   deadlocks).
4. See `docs/architecture/ADR-002-concurrency-strategy.md` for the
   comparison against optimistic locking and SERIALIZABLE isolation, and
   why pessimistic row locking was chosen for V1.

## Verification
Both load tests are part of the standard test suite
(`docker compose --profile test run tests`) and run on every CI execution,
so a regression in locking behaviour fails the build immediately rather
than surfacing as a production incident.
