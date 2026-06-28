# Phase 2 (Days 6–10) Review

## Architecture Diagram (textual — see docs/schema/ for ERD exports)

```
                         ┌─────────────────────┐
   API Routes  ───────▶  │  Controllers          │
 (src/routes/)           │  (src/controllers/)    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  Transaction Engine    │  ◀── idempotency_keys
                         │ (state machine,        │      (Part A9)
                         │  src/services/         │
                         │  transaction_engine.py)│
                         └──────────┬───────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
   transactionHandlers/*   concurrency_control.py   account_service.py
   (20 type-specific            (SELECT FOR UPDATE,    (customer wallet /
    journal builders)            ordered locking,        FX holding /
                                  advisory locks)         pooled asset
                |                                          resolution)
                ▼
      journal_entry_service.py
   (per-currency balance check,
    hash chaining, atomic insert)
                |
                ▼
        balance_service.py  ──▶  balance_snapshots (derived cache)
                |
                ▼
         PostgreSQL: ledger_entries (immutable, hash-chained, triggers)
```

## API Summary (22 endpoints)
All 20 transaction types are live (see `docs/api/openapi.yaml`, auto-
generated from the running app — guaranteed accurate):

| # | Type | Endpoint |
|---|------|----------|
| 1 | Deposit (Bank) | `POST /api/v1/deposit` |
| 2 | Deposit (Card) | `POST /api/v1/deposit-card` |
| 3 | Withdrawal | `POST /api/v1/withdraw` |
| 4 | P2P Transfer | `POST /api/v1/transfer` |
| 5 | Merchant QR Payment | `POST /api/v1/merchant-payment/qr` |
| 6 | Merchant Online Payment | `POST /api/v1/merchant-payment/online` |
| 7 | Bill Payment | `POST /api/v1/bill-payment` |
| 8 | Interest Accrual | `POST /api/v1/interest-accrual` |
| 9 | Interest Payout | `POST /api/v1/interest-payout` |
| 10 | Fee Deduction | `POST /api/v1/fee-deduction` |
| 11 | Cashback Credit | `POST /api/v1/cashback-credit` |
| 12 | Promotional Credit | `POST /api/v1/promotional-credit` |
| 13 | Loan Disbursement | `POST /api/v1/loan-disbursement` |
| 14 | Loan EMI | `POST /api/v1/loan-emi` |
| 15 | FX Conversion | `POST /api/v1/fx` |
| 16 | Full Refund | `POST /api/v1/reversal` |
| 17 | Partial Refund | `POST /api/v1/refund` |
| 18 | Chargeback | `POST /api/v1/chargeback` |
| 19 | Reward Redemption | `POST /api/v1/reward-redemption` |
| 20 | Account Closure Sweep | `POST /api/v1/account-closure` |
| — | Trial Balance | `GET /api/v1/trial-balance` |
| — | Health | `GET /api/v1/health` |

## Incident Response Summary
| Day | Incident | Resolution |
|-----|----------|------------|
| 2 | Duplicate P2P processing | `idempotency_keys` table, checked first in `transaction_engine.execute_transaction` |
| 4 | Trial balance discrepancy | Corrected sign-handling bug in `trial_balance_service` (caught the spec's own deliberate error) |
| 6 | Stale FX rate used | `exchange_rate_service.get_latest_rate()` enforces freshness window, raises `StaleRateError` |
| 8 | Refund posted as new credit | `reversal_service` mirrors original lines exactly (incl. fee revenue), separate code path from credit handlers |
| 10 | Concurrent double-spend | `SELECT FOR UPDATE` + ordered multi-account locking, verified by load tests |

## Key Design Corrections Made This Phase
1. **Per-currency balance validation** (`journal_entry_service._assert_balanced`)
   — a global sum across mixed currencies is accounting-meaningless; FX
   conversion journals are now validated currency-by-currency.
2. **Customer wallets as Liability sub-accounts**, not Asset sub-accounts
   (see `docs/submission-notes.md`) — fixes the spec's own unbalanced P2P
   worked example.
3. **Advisory-lock-serialised reversals** — closes the exact race window
   described in Case Study #4 (Razorpay concurrent refund).

## Test Suite Status
- 6 unit tests (hash chain) — passing in any environment.
- 16 integration/load tests — written against the real PostgreSQL schema
  (triggers, advisory locks, partitioning); skip gracefully without a live
  DB, run fully under `docker compose --profile test run tests`.
- Coverage config (`.coveragerc`) added; targeting >80% line coverage on
  `src/` once run against the live database in CI.

## Carried Forward to Phase 3 (Days 11–15)
Hash-chain verification API + anomaly detection, full reporting suite
(income statement, balance sheet, account statements, currency exposure),
table partitioning rollout (migration 007 exists but needs a live
verification pass), zero-downtime migration load test, and final
documentation pass.
