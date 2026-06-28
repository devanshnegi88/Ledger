# Incident Post-Mortem: Refund Processed as a New Credit, Not a Reversal

**Incident Card (Day 8):** A refund for a merchant payment was processed
as a new credit instead of a reversal. Revenue was double-counted.

## Root Cause
The legacy refund flow called the same "credit wallet" primitive used for
cashback/promotional credits, with no link back to the original
transaction. The original payment's fee-revenue entry was never reversed,
so the merchant's revenue line remained on the books even though the money
was returned to the customer — overstating P&L.

## Design Solution Implemented
1. **Reversals are structurally distinct from credits.** `reversal_service`
   is the *only* code path that creates `REVERSAL_FULL` / `REVERSAL_PARTIAL`
   reference-typed journal entries; cashback/promotional credit handlers
   are separate modules entirely and cannot accidentally double as refunds.
2. **Every reversal entry references the original** via
   `reference_id = original_transaction_id`, and mirrors the *exact* lines
   of the original transaction (account-for-account, including the fee
   revenue line) — so a reversed merchant payment correctly removes the
   fee revenue that was recognised, eliminating double-counting.
3. **`reversals` table with `UNIQUE(original_transaction_id, reversal_idempotency_key)`**
   plus a `_has_full_reversal()` check prevents a second full reversal of
   the same transaction outright (`RefundExceedsOriginalError`).
4. **Advisory lock per `original_transaction_id`** (Case Study #4) closes
   the race window where two concurrent refund requests could both pass
   an "already refunded?" check before either commits.
5. Trial balance is asserted to remain balanced after every reversal/refund
   in `tests/integration/test_reversal.py` — a regression here would show
   up immediately as a debit/credit mismatch, not just a hidden revenue
   overstatement.

## Verification
`test_full_reversal_mirrors_original_and_restores_balances` confirms the
sender's balance is restored exactly to its pre-transaction value (proving
the fee was also unwound, not just the principal), and that the trial
balance remains balanced throughout.
