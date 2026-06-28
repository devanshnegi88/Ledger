# Submission Notes

## Deliberate Errors Identified & Corrected

Per Section E5 ("the deliberate errors in Part A and Part C are a test"),
the following issues in the reference material were identified and
**corrected** in this implementation rather than copied verbatim:

### 1. Trial Balance query (Part A6.1)
The reference SQL computes `net_balance` as
`SUM(CASE WHEN entry_type='DEBIT' THEN amount ELSE -amount END)`
unconditionally for every account. This is only correct for Asset/Expense
accounts (normal balance = DEBIT). For Liability/Equity/Revenue accounts
(normal balance = CREDIT), it silently reports the balance with an
**inverted sign**.

**Fix:** `src/services/trial_balance_service.py` branches on
`account.account_type` (via `DEBIT_NORMAL_TYPES`) and computes
`debits - credits` for Asset/Expense and `credits - debits` for
Liability/Equity/Revenue, matching the standard accounting equation.

### 2. P2P Transfer worked example (Part A1.3, page 5)
The reference example posts:
```
Credit User A Wallet   5,010.00
Debit  User B Wallet   5,000.00
Credit Fee Revenue        10.00
```
Total debits = 5,000.00; total credits = 5,020.00 — **this journal does not
balance** (off by the fee amount). If implemented literally, every P2P
transfer with a non-zero fee would corrupt the trial balance.

**Fix:** see "Design Correction" below — fixing the imbalance required
reconsidering what account type "wallet" actually is.

### 3. Trial Balance / Journal Balance Check — Mixed Currencies (Phase 2)
The original Day 3 implementation summed debits/credits as one global
total regardless of currency. This works for single-currency journals but
is accounting-meaningless for multi-currency journals (FX Conversion,
Part A3.2) — comparing "100 USD debit" against "8,342 INR credit" as raw
numbers proves nothing about whether the journal is actually balanced.

**Fix:** `journal_entry_service._assert_balanced()` now groups lines by
`currency` and validates `SUM(debits) == SUM(credits)` independently for
each currency present in the journal. The FX Conversion handler
(`fx_conversion.py`) is built around this: the source-currency leg and
target-currency leg each balance on their own.

## Design Correction: Customer Wallets Modelled as Liability Sub-Accounts

The CoA (Part A1.2) classifies `1001/1002/1003` (Customer Wallet) as
**Asset** accounts and `2001` (Customer Deposit Liability) as a separate
**Liability** account. Taken together with the Deposit worked example
(Debit 1001 Asset / Credit 2001 Liability, both by the full deposit amount),
this implies `1001` is the bank's **pooled reserve** (total cash held on
behalf of all customers collectively), while each individual customer's
spendable balance lives as a liability the bank owes that specific customer.

The reference P2P example instead treats per-customer wallets as Asset
sub-accounts ("1001-A", "1001-B"), which is both internally inconsistent
with the Deposit example and the source of the imbalance above.

**Implementation:** `src/services/account_service.py` creates one Liability
sub-account per customer (`account_code = "2001:<customer_ref>:<currency>"`,
`normal_balance = CREDIT`) on first use. Consequences:
- **Deposit:** Debit pooled Asset (1001/1002/1003) / Credit customer's
  Liability sub-account — unchanged from the spec, and balances.
- **Withdrawal:** mirror of deposit — balances.
- **P2P Transfer:** Debit sender's Liability sub-account (amount + fee) /
  Credit recipient's Liability sub-account (amount) / Credit Fee Revenue
  (fee). Total debits = amount + fee = total credits. **Balances.**
- **Fee Deduction:** Debit customer's Liability sub-account / Credit Fee
  Revenue — matches the spec's stated pattern exactly, and is consistent
  with this model (a fee deduction decreases what the bank owes the
  customer, i.e. a debit to a credit-normal liability account).
- The bank's pooled reserve (1001/1002/1003) is untouched by P2P transfers,
  which is correct: a transfer between two customers doesn't change the
  bank's total cash position, only which customer it's owed to.

This is noted explicitly here per the project's AI-tools policy: the error
was caught by tracing the worked examples through to a failing balance
check rather than transcribing the reference material as-is.

## AI Assistance Acknowledgement
Built with assistance from Claude (Anthropic, Sonnet 4.6) for: repository
scaffolding, SQLAlchemy model/migration authoring, the hash-chaining
utility, the journal-entry/transaction-engine service layer, and test
generation. All schema design decisions, the accounting-model correction
above, and the concurrency strategy (ADR-002) were reviewed against the
project specification's Part A reference material and verified against
the double-entry accounting equation by hand before being committed.

## Known Limitation: Balance Sheet `is_balanced` (Day 12)
`reporting_service.generate_balance_sheet()` exposes an `is_balanced`
property (`Assets == Liabilities + Equity`) per Part A6.3, but this will
**not** evaluate to `True` in the current implementation: Revenue and
Expense account balances are never closed into Retained Earnings (account
3001) via a period-close process. Real accounting systems run a "closing
entry" batch job at period-end that zeros out P&L accounts into equity —
this is intentionally out of scope for Phase 3 and tracked as a later
item. The integration test for this report (`test_reporting.py`) does
**not** assert `is_balanced`, to avoid the test suite implying a
correctness guarantee the system doesn't yet provide. Flagging this
explicitly rather than silently shipping a misleading green checkmark.

## Known Limitations (Phase 2 status)
- Daily/per-tier transaction limits (KYC tiers, LRS quotas) are stubbed —
  not yet wired to a rules table.
- All 20 transaction types are now implemented (Phase 2 complete). Audit
  verification API, full reporting suite (income statement, balance
  sheet, account statements, currency exposure), partition rollout
  verification, and scheduler jobs (FX revaluation, interest accrual
  batch, trial balance batch) are scheduled for Phase 3 (Days 11–15).
- Reward Points Liability (account 2030) and the reuse of account 5002
  for both Cashback and Promotional credit are documented Phase 1
  additions/simplifications beyond the original 19-account CoA — see
  above.
- Integration tests require a live PostgreSQL instance (triggers,
  advisory locks, partitioning are Postgres-specific) — they skip
  gracefully in environments without one and run fully under
  `docker compose --profile test run tests`.
