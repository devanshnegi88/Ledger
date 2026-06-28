# ADR-002: Concurrency Strategy Selection

**Status:** Accepted
**Date:** 2026-06-20

## Context
Part A4.3 requires preventing double-spend when concurrent requests touch
the same account(s). Case Study #4 (Razorpay concurrent refund) and
Incident Card Day 10 both describe the canonical failure mode: two
concurrent requests both read a balance/state as "OK" before either
commits, and both proceed.

## Options Considered
1. **Pessimistic locking** (`SELECT ... FOR UPDATE`)
2. **Optimistic locking** (version column + compare-and-swap)
3. **SERIALIZABLE isolation** (Postgres SSI, abort-and-retry)
4. **Advisory locks** (`pg_advisory_xact_lock`)

## Decision
**Pessimistic row locking on the account row**, combined with
**deterministic lock ordering** (always lock multiple accounts in ascending
UUID order — see `concurrency_control.lock_accounts_for_update_ordered`)
for multi-account operations like P2P transfer.

### Why not the alternatives (for V1)
- *Optimistic locking* needs explicit retry loops at the caller; under the
  high-contention "50 concurrent withdrawals on one account" test (Day 7
  acceptance criteria) this produces retry storms that are harder to bound
  than a simple lock-wait queue.
- *SERIALIZABLE SSI* is the theoretically cleanest option (no explicit
  locks) but requires every caller to catch `serialization_failure` and
  retry the whole transaction — more invasive to retrofit across 20
  transaction handlers in this phase. `concurrency_control.with_serializable_isolation()`
  is provided so it can be benchmarked head-to-head against pessimistic
  locking in Day 7's load test.
- *Advisory locks* trade row-level blocking for an extra moving part
  (lock-key derivation, cleanup on crash) without a clear win here since
  our hot path already touches the account row directly.

## Deadlock Prevention
A P2P transfer locks two accounts. If transfer A→B and a concurrent
transfer B→A both started, naive code could lock in opposite orders and
deadlock. We always sort account IDs and lock in ascending order
(`lock_accounts_for_update_ordered`), so both transactions always request
locks in the same global order — one waits, neither deadlocks.

## Benchmark Plan (Day 7)
`tests/load/concurrent-withdrawal.test.py` fires 50 concurrent withdrawal
requests of INR 500 each against an account with INR 10,000 balance.
Expected: exactly 20 succeed, 30 fail with `InsufficientBalanceError`, zero
deadlocks, and the account balance never goes negative.

## Consequences
- Throughput on a single hot account is serialized (by design — this is
  the whole point of preventing double-spend).
- Lock wait timeouts must be configured (`statement_timeout` /
  `lock_timeout` at the connection-pool level) to avoid unbounded queuing
  under pathological contention; this is tracked as a Phase 2 hardening
  item.
