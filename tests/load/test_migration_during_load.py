"""
tests/load/test_migration_during_load.py — Day 14

Runs continuous deposit traffic in background threads while a non-blocking
schema change (an additional nullable column, mirroring migration 006's
pattern) is applied, and asserts zero failed requests during the window —
proving the migration did not require any downtime.
"""
import threading
import time
import uuid
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.validators.schemas import DepositBankRequest
from src.services.transactionHandlers.deposit import process_deposit_bank

TEST_COLUMN_NAME = "load_test_marker_column"


def _continuous_deposit_worker(stop_event: threading.Event, errors: list, successes: list):
    engine = create_engine(settings.database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            process_deposit_bank(db, DepositBankRequest(
                account_code=f"cust-migload-{uuid.uuid4().hex[:6]}",
                amount=Decimal("10.0000"), currency="INR",
                idempotency_key=f"migload-{uuid.uuid4().hex}", created_by="migration-load-test",
            ))
            db.commit()
            successes.append(1)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            errors.append(str(exc))
        finally:
            db.close()
        time.sleep(0.01)
    engine.dispose()


def test_zero_downtime_add_column_during_continuous_load(db_engine, db_session):
    # Clean up from any previous failed run.
    db_session.execute(text(f"ALTER TABLE accounts DROP COLUMN IF EXISTS {TEST_COLUMN_NAME}"))
    db_session.commit()

    errors: list = []
    successes: list = []
    stop_event = threading.Event()

    threads = [
        threading.Thread(target=_continuous_deposit_worker, args=(stop_event, errors, successes))
        for _ in range(5)
    ]
    for t in threads:
        t.start()

    time.sleep(0.3)  # let traffic ramp up before the migration

    # Non-blocking ADD COLUMN — mirrors migrations/006's pattern exactly.
    migrate_engine = create_engine(settings.database_url, future=True)
    with migrate_engine.begin() as conn:
        conn.execute(text(
            f"ALTER TABLE accounts ADD COLUMN {TEST_COLUMN_NAME} BOOLEAN DEFAULT false"
        ))
    migrate_engine.dispose()

    time.sleep(0.3)  # keep traffic flowing briefly after the migration too

    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    # Cleanup
    db_session.execute(text(f"ALTER TABLE accounts DROP COLUMN IF EXISTS {TEST_COLUMN_NAME}"))
    db_session.commit()

    assert len(successes) > 0, "No successful deposits were recorded during the test window"
    assert errors == [], f"Migration caused {len(errors)} failed requests: {errors[:3]}"
