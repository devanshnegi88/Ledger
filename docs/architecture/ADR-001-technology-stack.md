# ADR-001: Technology Stack Selection

**Status:** Accepted
**Date:** 2026-06-20

## Context
The ledger system requires strict transactional correctness, native support
for arbitrary-precision decimals, mature concurrency primitives (row locks,
SERIALIZABLE isolation, advisory locks), and a migration tool with full
control over raw DDL (triggers, partitioning, CONCURRENTLY index builds).

## Decision
- **Language/Framework:** Python 3.11 + FastAPI — async-capable, strong
  typing via Pydantic v2, excellent OpenAPI auto-generation.
- **Database:** PostgreSQL 15 — mandatory per spec; native range
  partitioning, advisory locks, SERIALIZABLE SSI, triggers.
- **ORM:** SQLAlchemy 2.0 (Core + ORM) — explicit control over
  transactions, `SELECT ... FOR UPDATE`, raw SQL escape hatches for
  triggers/partitioning that the ORM cannot express declaratively.
- **Migrations:** Alembic — versioned, supports raw SQL migrations
  (required for trigger functions and partition DDL).
- **Scheduler:** APScheduler — in-process cron-style jobs for FX
  revaluation, interest accrual, trial balance generation.
- **Caching:** Redis — optional balance-snapshot cache layer.
- **Auth:** JWT (python-jose) — stateless, horizontally scalable.

## Consequences
- Decimal arithmetic uses `NUMERIC(19,4)` / Python `Decimal` everywhere —
  never `float` (Anti-Pattern #1, Revolut Case Study #2).
- Raw SQL is used for triggers and `CREATE INDEX CONCURRENTLY` since these
  cannot be expressed through the SQLAlchemy ORM layer.
- FastAPI's async support is available but the V1 transaction engine uses
  synchronous SQLAlchemy sessions for simplicity around `SELECT FOR UPDATE`
  semantics; an async session pool can be introduced later without
  changing the service-layer contracts.
