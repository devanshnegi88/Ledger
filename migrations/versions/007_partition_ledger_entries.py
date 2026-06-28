"""007 partition ledger_entries by effective_date (monthly range partitions)

Revision ID: 007
Revises: 006
Create Date: 2026-06-20

PostgreSQL native partitioning (Part A7.2). Since converting an existing
table to partitioned requires a rebuild, this migration creates the
partitioned structure as `ledger_entries_p`, copies data across, and swaps
names — documented here for clarity; in a live system this would run via
the blue/green pattern in scripts/manage_partitions.py during a low-traffic
window, NOT a blocking ALTER TABLE.
"""
from alembic import op
import sqlalchemy as sa
import datetime

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ledger_entries_p (
            LIKE ledger_entries
        ) PARTITION BY RANGE (effective_date);
    """)

    # Create partitions for the current and next 2 months; ongoing partitions
    # are managed by scripts/manage_partitions.py (a scheduled APScheduler job).
    today = datetime.date.today().replace(day=1)
    for i in range(3):
        month_start = _add_months(today, i)
        month_end = _add_months(today, i + 1)
        partition_name = f"ledger_entries_{month_start.strftime('%Y_%m')}"
        op.execute(f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF ledger_entries_p
            FOR VALUES FROM ('{month_start.isoformat()}') TO ('{month_end.isoformat()}');
        """)

    op.execute("INSERT INTO ledger_entries_p SELECT * FROM ledger_entries;")
    op.execute("ALTER TABLE ledger_entries RENAME TO ledger_entries_legacy;")
    op.execute("ALTER TABLE ledger_entries_p RENAME TO ledger_entries;")


def downgrade() -> None:
    op.execute("ALTER TABLE ledger_entries RENAME TO ledger_entries_p;")
    op.execute("ALTER TABLE ledger_entries_legacy RENAME TO ledger_entries;")
    op.execute("DROP TABLE IF EXISTS ledger_entries_p CASCADE;")


def _add_months(d: datetime.date, months: int) -> datetime.date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    return datetime.date(year, month, 1)
