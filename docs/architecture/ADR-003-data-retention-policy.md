# ADR-003: Data Retention & Archival Policy

**Status:** Accepted
**Date:** 2026-06-20

## Context
Part A7.1 requires a tiered retention policy and RBI mandates a 10-year
minimum retention period for banking records.

## Decision
| Tier | Age | Storage | Mechanism |
|------|-----|---------|-----------|
| Hot | 0–90 days | Primary PostgreSQL, full indexing | Current/recent monthly partitions of `ledger_entries` |
| Warm | 90 days – 7 years | Partitioned tables, reduced indexing | Older monthly partitions remain attached but are candidates for a read-replica |
| Cold | 7+ years | Object storage (S3-compatible), CSV/Parquet | `scripts/archive_partition.py` exports + detaches + drops the partition table |

Partitioning is by `effective_date`, monthly granularity
(`migrations/007_partition_ledger_entries.py`), matching the spec's
worked example exactly (`ledger_entries_YYYY_MM`).

## Lifecycle
1. `scripts/manage_partitions.py create-future` runs monthly (via
   APScheduler) to ensure the next 3 months' partitions always exist
   before they're needed — partition creation must never be on the
   critical path of a live insert.
2. Partitions older than 7 years are detached
   (`manage_partitions.py detach <name>`) — this is instantaneous (no data
   movement) and immediately removes the table from query planning for
   the parent `ledger_entries`.
3. The detached, now-standalone table is exported via
   `archive_partition.py` to CSV (Parquet in production) and optionally
   dropped after a successful export, freeing primary storage.

## Why CSV Instead of Parquet in This Phase
Parquet requires `pyarrow`, a heavyweight optional dependency. The export
function in `archive_partition.py` is isolated so swapping the writer is
a one-function change; CSV demonstrates the archival *mechanism*
(detach → export → drop) without forcing every contributor to install a
large binary dependency for a Phase 3 exercise.

## Consequences
- Detaching a partition is metadata-only and fast; the actual data export
  is the slow part and runs as an offline batch, not inline with any
  customer-facing request.
- Regulatory holds (litigation, ongoing investigation) would need a flag
  to *skip* archival for specific date ranges — not yet implemented;
  tracked as a follow-up.
