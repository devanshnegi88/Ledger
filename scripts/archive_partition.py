"""
scripts/archive_partition.py

Day 13 — archival script: exports a detached partition to CSV (a stand-in
for Parquet in this Phase, since pyarrow is an optional heavy dependency;
swap the writer for pyarrow.parquet.write_table in production), then drops
the now-redundant standalone table.

Usage:
    python scripts/archive_partition.py ledger_entries_2025_03 --output-dir /archive
"""
import argparse
import csv
import sys
from pathlib import Path

from sqlalchemy import text

from src.config.database import engine


def export_partition_to_csv(partition_name: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{partition_name}.csv"

    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM {partition_name}"))
        columns = result.keys()
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in result:
                writer.writerow(row)

    return output_path


def drop_partition_table(partition_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {partition_name};"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("partition_name")
    parser.add_argument("--output-dir", type=str, default="/archive")
    parser.add_argument("--drop-after-export", action="store_true")
    args = parser.parse_args()

    output_path = export_partition_to_csv(args.partition_name, Path(args.output_dir))
    print(f"Exported {args.partition_name} -> {output_path}")

    if args.drop_after_export:
        drop_partition_table(args.partition_name)
        print(f"Dropped table {args.partition_name} after successful export.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
