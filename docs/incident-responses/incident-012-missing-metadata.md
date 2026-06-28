# Incident Post-Mortem: Entries Without Creator Metadata

**Incident Card (Day 12):** Compliance audit found 340 entries without
creator metadata. Cannot trace who initiated these transactions.

## Root Cause
The legacy system allowed `created_by` to be nullable at the database
level, relying entirely on application code to populate it. A code path
(likely a batch job or admin tool) inserted entries without going through
the standard request pipeline, silently leaving the field NULL.

## Design Solution Implemented
1. **`ledger_entries.created_by` is `NOT NULL`** at the database level
   (`migrations/002`) — this was built in from Day 2, not added reactively,
   precisely to prevent this incident class from being possible at all.
2. **Every transaction handler requires `created_by`** in its Pydantic
   request schema (`Field(...)` with no default in most schemas; scheduler-
   triggered types like `InterestAccrualRequest` default to
   `"system-scheduler"` rather than allowing it to be omitted).
3. **`Transaction.created_by` is also `NOT NULL`**, so even if a future
   batch job bypasses individual ledger-entry creation paths, the
   transaction record itself still carries an attributable actor.
4. Any attempt to insert a row violating these constraints fails at the
   database level with a clear `NOT NULL constraint` error — fast,
   visible failure at write-time rather than a silent gap discovered
   months later during an audit.

## Verification
Every integration test in this suite asserts (implicitly, by virtue of
the schema requiring it) that `created_by` is populated — there is no code
path in `src/services/transactionHandlers/*` that constructs a
`LineInput`/`LedgerEntry` without it.
