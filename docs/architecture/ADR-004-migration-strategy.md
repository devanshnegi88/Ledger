# ADR-004: Schema Migration Strategy

**Status:** Accepted
**Date:** 2026-06-20

## Context
Part A7.3 requires versioned migrations, a rollback story, and a
zero-downtime approach — directly motivated by Incident Card Day 14
(a 4-hour outage for a schema migration caused every in-flight
transaction to fail).

## Decision
- **Tool:** Alembic, with both ORM-driven (`op.create_table`, etc.) and
  raw-SQL migrations (triggers, `CREATE INDEX CONCURRENTLY`, partitioning)
  in the same versioned chain.
- **8 migrations exist** (`migrations/versions/001`–`008`), demonstrating:
  initial schema creation (001–002), trigger-based immutability (003),
  supporting tables (004), concurrent index creation (005), non-blocking
  column addition (006), table partitioning (007), and a singleton
  hash-chain pointer table (008).
- **Every migration has a `downgrade()`** — the rollback story is the
  migration file itself, not separate documentation that can drift out of
  sync with the forward migration.

## Zero-Downtime Rules Followed
1. `ALTER TABLE ... ADD COLUMN` with a constant default and `nullable=True`
   (migration 006) — non-blocking in PostgreSQL 11+, no full table rewrite.
2. `CREATE INDEX CONCURRENTLY` (migration 005) — does not take a write lock
   on the table; existing reads/writes are unaffected during index
   construction. **Caveat:** this cannot run inside Alembic's default
   transactional-DDL wrapper (`CONCURRENTLY` is not transaction-safe); see
   `scripts/run_concurrent_migration.sh` for the non-transactional
   invocation required.
3. **Never** `ALTER TABLE ... ALTER COLUMN TYPE` — this requires a full
   table rewrite and would block all access for the duration; if a type
   change is ever needed, the pattern is add-new-column →
   backfill-in-batches → swap-reads-to-new-column → drop-old-column,
   each step independently non-blocking.
4. Partition creation (migration 007, and `scripts/manage_partitions.py`)
   is metadata-only for *creating* a partition — it does not lock existing
   partitions.

## Verification
`tests/load/test_migration_during_load.py` runs continuous deposit
traffic in a background thread while migration 006 (`ADD COLUMN`) is
applied, and asserts zero failed requests during the migration window.

## Consequences
- `CREATE INDEX CONCURRENTLY` (migration 005) cannot run inside a
  transaction block. Rather than disabling transactional DDL globally,
  it's wrapped in `with op.get_context().autocommit_block():` for just
  that one operation — every other migration in the chain remains
  transactional as normal.
