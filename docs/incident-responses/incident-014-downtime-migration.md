# Incident Post-Mortem: 4-Hour Outage for Schema Migration

**Incident Card (Day 14):** A database maintenance window required a
4-hour outage for schema migration. All transactions failed during the
window.

## Root Cause
The legacy migration added a new required column using a pattern that
forces a full table rewrite under lock — e.g. `ALTER TABLE ... ADD COLUMN
... NOT NULL DEFAULT <computed-per-row-value>`, or building an index with
a plain `CREATE INDEX` (which takes a write lock for the duration). On a
large `ledger_entries` table, this took hours and blocked all writes (and
on some Postgres versions, reads) for the duration.

## Design Solution Implemented
1. **`ADD COLUMN` with a constant default, nullable** (migration 006) —
   PostgreSQL 11+ handles this as a metadata-only change; it does not
   rewrite existing rows or take a long-held lock.
2. **`CREATE INDEX CONCURRENTLY`** (migration 005) instead of a plain
   `CREATE INDEX` — builds the index without blocking concurrent
   reads/writes, at the cost of a slower build and the (rare) need to
   retry if it's interrupted. Wrapped in `autocommit_block()` since it
   cannot run inside Alembic's default transactional DDL.
3. **Never `ALTER TABLE ... ALTER COLUMN TYPE`** — documented in ADR-004
   as a hard rule; any future type change follows an add/backfill/swap/drop
   pattern instead.
4. **Verified empirically, not just asserted:**
   `tests/load/test_migration_during_load.py` runs continuous deposit
   traffic across 5 threads while a non-blocking `ADD COLUMN` is applied
   live, and asserts zero failed requests during the entire window.

## Verification
The load test is part of the standard suite and fails loudly (non-empty
`errors` list) if any future migration regresses to a blocking pattern.
