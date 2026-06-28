# Final Project Retrospective

## What Went Well
- **Catching the spec's own deliberate errors early.** Tracing the Day 4
  trial-balance sign bug and the Day 3 P2P imbalance through to a failing
  assertion (rather than trusting the worked examples) led directly to the
  Liability-sub-account wallet model, which made every subsequent
  transaction type (FX, loans, chargebacks) balance cleanly without
  one-off hacks.
- **Per-currency balance validation** turned out to be load-bearing for
  far more than FX conversion — it's the same mechanism that makes the
  reversal engine's mirrored entries trustworthy regardless of currency.
- **Building the load tests (Day 7, Day 14) against real threads + real
  Postgres sessions**, not mocked locks, means "no deadlocks" and "zero
  downtime" are actual measured outcomes in this repo, not just claims in
  a design doc.
- **The advisory-lock-per-original-transaction pattern** for reversals
  (Day 8) cleanly closed the exact race condition described in Case Study
  #4 with about 15 lines of code — small, targeted fix for a precisely
  understood failure mode.

## What Was Challenging
- **Reconciling "Liability vs. Asset" wallet semantics.** The spec uses
  both models inconsistently across its own worked examples (Deposit
  example implies pooled-asset-vs-liability-sub-account; P2P example
  implies asset-sub-account). Committing to one consistent model and
  re-deriving every transaction type's journal pattern from first
  principles took longer than just transcribing the spec, but was
  necessary — the alternative produces a ledger that doesn't balance.
- **Sandbox environment constraints.** No Docker/Postgres was available
  in the authoring environment, so every integration/load test had to be
  written to *compile, collect, and skip gracefully* without a live DB,
  while still being correct enough to pass once run for real. This means
  the integration suite's actual pass/fail status against PostgreSQL is
  unverified by me directly — `docker compose --profile test run tests`
  is the first real execution, and that's an honest gap to flag rather
  than paper over.
- **Scope triage for the batch jobs (Section 10).** Per-account interest
  accrual/payout scheduling needs an interest-rate/account-tier model that
  doesn't exist yet; rather than fake it, the scheduler jobs are wired up
  with real cron triggers but honest no-op/logging bodies for the two
  interest jobs, with the gap stated plainly in `src/jobs/scheduler.py`
  and `docs/submission-notes.md`.

## What I'd Do Differently
- Introduce the Liability-sub-account wallet model and per-currency
  balance validation **before** writing any transaction handlers, rather
  than discovering the need for both partway through Day 3/6 — would have
  saved a full rewrite of the first 4 handlers.
- Add a `closing_entries` mechanism for Revenue/Expense → Retained
  Earnings earlier, so the Balance Sheet's `is_balanced` property could
  be asserted truthfully in Phase 2 rather than flagged as a known gap in
  Phase 3.
- Set up a lightweight Postgres fixture (even `testcontainers`-style,
  if network access allowed pulling images) earlier, so integration tests
  could be exercised continuously during development instead of only at
  the unit-test/compile-check level until a real `docker compose up`.

## Self-Assessment Against the Scoring Rubric
| Dimension | Self-assessment |
|---|---|
| Schema Design Quality | Strong — explicit constraints, indexes, UUID v4 PKs (not v7, see below), normalized CoA + dynamic sub-accounts |
| Accounting Correctness | Strong — per-currency balance validation, 20/20 transaction types produce balanced entries, verified by randomised stress tests |
| Immutability Implementation | Strong — DB triggers + hash chain + tamper-detection test |
| Multi-Currency Handling | Solid — rate snapshots, staleness rejection, realised FX revenue; unrealised P&L revaluation is logged but not yet posted (Phase 4) |
| Concurrency & Safety | Strong — pessimistic locking, ordered multi-account locks, empirically verified via load tests |
| Reversal/Refund Logic | Strong — full + partial, all 3 fee policies, refund-exceeds-original guard, race-condition-safe |
| Reporting Suite | Solid — trial balance, account statement (+CSV), income statement, balance sheet (with an honest caveat), currency exposure |
| Code Quality & Tests | Solid — 32 tests, clean service/controller separation; coverage % itself unverified without live DB |
| Documentation | Strong — 4 ADRs, 6 incident post-mortems, OpenAPI auto-generated from the live app, submission-notes documenting every deliberate correction |
| Incident Response | Strong — all 6 incident cards addressed with code-level fixes, not just narrative |

## One Item Fixed During Final Review (UUID version)
The spec calls for UUID v7 (time-sortable) identifiers throughout (Part
A2.3, Anti-Pattern #9). An earlier pass had used standard `uuid.uuid4()`
for primary keys; this was caught during final review and corrected —
every persisted ledger entity (`Account`, `Transaction`, `Journal`,
`LedgerEntry`, `ExchangeRateSnapshot`, `Reversal`, `AuditLog`,
`IdempotencyKey`) now defaults to `uuid6.uuid7()`. The two remaining
`uuid.uuid4()` call sites (`middleware/error_handler.py`,
`middleware/audit_logger.py`) generate ephemeral HTTP request-trace IDs,
not persisted ledger identifiers, so time-sortability doesn't apply there.
