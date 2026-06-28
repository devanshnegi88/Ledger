# Phase 1 (Days 1–5) Self-Assessment Checklist

## Day 1 — Repository Setup, Environment & Chart of Accounts
- [x] GitHub-ready repo structure matching the mandatory layout exactly
- [x] `docker-compose.yml` (Postgres 15 + Redis + app + tests profile)
- [x] `Dockerfile`, `.env.example`
- [x] 19-account Chart of Accounts seeded (`seeds/chart_of_accounts.sql`)
- [x] `migrations/001_create_accounts_table.py`
- [x] ADR-001 (technology stack)

## Day 2 — Ledger Entry Schema & Hash Chain Foundation
- [x] `ledger_entries` table with all Part A2.3 columns
- [x] SHA-256 hash chaining (`src/utils/hash.py`) — global chain via
      `hash_chain_state` singleton, locked with `SELECT ... FOR UPDATE`
- [x] DB constraints: `amount > 0`, `NOT NULL` audit fields, `UNIQUE`
      idempotency key
- [x] `BEFORE UPDATE`/`BEFORE DELETE` triggers blocking mutation of posted
      entries (`migrations/003`)
- [x] 6 passing hash-chain unit tests
- [x] Incident #2 post-mortem (duplicate processing / idempotency)

## Day 3 — Journal Entry Processing Engine
- [x] `journal_entry_service.create_journal_entry()` — balance validation,
      hash chaining, atomic persistence
- [x] Balance validation rejects unbalanced journals (`UnbalancedJournalError`)
- [x] 4 transaction handlers: Deposit (Bank), Withdrawal, P2P Transfer, Fee
      Deduction
- [x] All journal inserts wrapped in `db_transaction()` (atomic
      commit/rollback)
- [x] Integration tests for all 4 (skip gracefully without live Postgres,
      run fully under `docker compose --profile test run tests`)

## Day 4 — Trial Balance & Balance Derivation
- [x] `trial_balance_service.generate_trial_balance()` with **corrected**
      sign handling per account normal-balance direction (see
      `docs/submission-notes.md` — spec's reference query had this wrong)
- [x] `balance_service` — balances derived from `SUM(debits)-SUM(credits)`,
      never stored as a mutable column (Anti-Pattern #2 guard);
      `balance_snapshots` is a self-healing read cache
- [x] `GET /api/v1/trial-balance` with `as_of_date` filtering
- [x] `test_trial_balance_after_100_random_transactions` — 100+ randomised
      transactions across types 1–4, asserts `total_debits == total_credits`

## Day 5 — Transaction Types 5–8 & API Documentation
- [x] Merchant QR Payment, Merchant Online Payment, Bill Payment, Interest
      Accrual handlers
- [x] `docs/api/openapi.yaml` — auto-generated from the live FastAPI app
      (guaranteed accurate, not hand-maintained)
- [x] `AuditLoggingMiddleware` — structured request/response logging with
      `X-Request-Id` tracing
- [x] This checklist

## Verified
- All `src/**/*.py` compile cleanly.
- `pytest` collects 13 tests (6 unit passing, 7 integration skipping
  gracefully without a live DB — by design, see `tests/conftest.py`).
- FastAPI app boots and exposes exactly the 10 expected routes (8
  transaction-type endpoints + health check + trial balance).

## Carried Forward to Phase 2 (Days 6–10)
Multi-currency / FX conversion, SERIALIZABLE-isolation benchmark vs.
pessimistic locking (Day 7), full reversal/refund engine, transaction
types 9–14 and 18–20, mid-project comprehensive test run with coverage
report.
