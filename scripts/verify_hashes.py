"""
scripts/verify_hashes.py

CLI script for hash chain verification (Day 11 deliverable).
Usage:
    python scripts/verify_hashes.py [--from-date YYYY-MM-DD] [--to-date YYYY-MM-DD]
Exit code 0 if the chain is intact, 1 if a break is detected.
"""
import argparse
import sys
from datetime import datetime

from src.config.database import SessionLocal
from src.services.audit_service import verify_hash_chain


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the ledger's global hash chain.")
    parser.add_argument("--from-date", type=str, default=None)
    parser.add_argument("--to-date", type=str, default=None)
    args = parser.parse_args()

    from_date = datetime.fromisoformat(args.from_date) if args.from_date else None
    to_date = datetime.fromisoformat(args.to_date) if args.to_date else None

    db = SessionLocal()
    try:
        result = verify_hash_chain(db, from_date, to_date)
    finally:
        db.close()

    print(f"Checked {result.total_entries_checked} entries.")
    if result.is_intact:
        print("Hash chain is INTACT.")
        return 0

    print("Hash chain is BROKEN.")
    print(f"  First broken entry: {result.first_break_entry_id}")
    print(f"  Reason: {result.break_reason}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
