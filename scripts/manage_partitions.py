"""
scripts/manage_partitions.py

Day 13 — Part A7.2 partition lifecycle management. Designed to be run as
a scheduled APScheduler job (monthly) once ledger_entries is partitioned
(migration 007).

Subcommands:
  create-future   — ensure partitions exist for the next N months
  list             — list existing partitions and their date ranges
  detach           — detach a named partition (does NOT drop it — see
                     archive_partition.py for the export+drop flow)
"""
import argparse
import datetime
import sys

from sqlalchemy import text

from src.config.database import engine


def _add_months(d: datetime.date, months: int) -> datetime.date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    return datetime.date(year, month, 1)


def create_future_partitions(months_ahead: int = 3) -> None:
    today = datetime.date.today().replace(day=1)
    with engine.begin() as conn:
        for i in range(months_ahead):
            start = _add_months(today, i)
            end = _add_months(today, i + 1)
            name = f"ledger_entries_{start.strftime('%Y_%m')}"
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {name}
                PARTITION OF ledger_entries
                FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}');
            """))
            print(f"Ensured partition {name} [{start} - {end})")


def list_partitions() -> None:
    query = text("""
        SELECT child.relname AS partition_name,
               pg_get_expr(child.relpartbound, child.oid) AS bounds
        FROM pg_inherits
        JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE parent.relname = 'ledger_entries'
        ORDER BY child.relname;
    """)
    with engine.connect() as conn:
        rows = conn.execute(query).all()
    for name, bounds in rows:
        print(f"{name}: {bounds}")


def detach_partition(partition_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE ledger_entries DETACH PARTITION {partition_name};"))
    print(f"Detached {partition_name} (still exists as a standalone table — not dropped).")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    create_p = sub.add_parser("create-future")
    create_p.add_argument("--months-ahead", type=int, default=3)

    sub.add_parser("list")

    detach_p = sub.add_parser("detach")
    detach_p.add_argument("partition_name")

    args = parser.parse_args()

    if args.command == "create-future":
        create_future_partitions(args.months_ahead)
    elif args.command == "list":
        list_partitions()
    elif args.command == "detach":
        detach_partition(args.partition_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
