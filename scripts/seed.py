"""
scripts/seed.py
Idempotent seed runner: applies seeds/chart_of_accounts.sql and
seeds/exchange_rates.sql. Safe to run multiple times (ON CONFLICT DO NOTHING).
"""
import pathlib
from sqlalchemy import text
from src.config.database import engine

SEEDS_DIR = pathlib.Path(__file__).resolve().parent.parent / "seeds"


def run_seed_file(filename: str) -> None:
    sql_path = SEEDS_DIR / filename
    sql = sql_path.read_text()
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))  # for gen_random_uuid()
        conn.execute(text(sql))
    print(f"Seeded: {filename}")


if __name__ == "__main__":
    run_seed_file("chart_of_accounts.sql")
    run_seed_file("exchange_rates.sql")
    print("Seeding complete.")
