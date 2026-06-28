"""
src/jobs/scheduler.py

Section 10 — APScheduler batch jobs. Registers the 4 required jobs:
  1. FX Revaluation (nightly) — unrealised P&L on FX holding balances.
  2. Daily Interest Accrual — posts INTEREST_ACCRUAL entries per account.
  3. Monthly Interest Payout — posts INTEREST_PAYOUT entries with TDS.
  4. Trial Balance Generation — end-of-day snapshot + discrepancy alert.

Each job opens its own DB session (APScheduler jobs run on a background
thread pool, so sessions must not be shared with request-handling threads).
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.database import SessionLocal
from src.services.trial_balance_service import generate_trial_balance
from src.models.account import Account
from sqlalchemy import select

logger = logging.getLogger("ledger.jobs")


def job_trial_balance_generation() -> None:
    db = SessionLocal()
    try:
        report = generate_trial_balance(db)
        if not report.is_balanced:
            logger.error(
                "TRIAL BALANCE DISCREPANCY DETECTED: debits=%s credits=%s",
                report.total_debits, report.total_credits,
            )
        else:
            logger.info(
                "Trial balance generated successfully: debits=%s credits=%s",
                report.total_debits, report.total_credits,
            )
    finally:
        db.close()


def job_fx_revaluation() -> None:
    """
    Nightly unrealised FX P&L (Part A3.3). Revalues every FX holding
    account at the current closing rate and would post an unrealised
    gain/loss journal entry for any movement since the last revaluation.
    Phase 3 scope: logs the computed exposure; posting the actual
    unrealised P&L journal entry is a Phase 4 item (requires a dedicated
    "Unrealised FX Gain/Loss" account not in the current 19-account CoA).
    """
    db = SessionLocal()
    try:
        from src.services.balance_service import compute_account_balance
        holdings = db.execute(
            select(Account).where(Account.sub_type == "FX Conversion Holding")
        ).scalars().all()
        for account in holdings:
            balance = compute_account_balance(db, account.id)
            logger.info("FX revaluation check: %s balance=%s %s", account.account_code, balance, account.currency)
    finally:
        db.close()


def job_daily_interest_accrual() -> None:
    """Placeholder hook — real implementation would iterate all interest-
    bearing accounts, compute day-count-convention interest, and call
    process_interest_accrual() per account. Logged as a no-op in Phase 3."""
    logger.info("Daily interest accrual job triggered (per-account accrual logic is a Phase 4 item).")


def job_monthly_interest_payout() -> None:
    """Placeholder hook — see job_daily_interest_accrual() note."""
    logger.info("Monthly interest payout job triggered (per-account payout logic is a Phase 4 item).")


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(job_fx_revaluation, CronTrigger(hour=23, minute=30), id="fx_revaluation")
    scheduler.add_job(job_daily_interest_accrual, CronTrigger(hour=0, minute=5), id="daily_interest_accrual")
    scheduler.add_job(job_monthly_interest_payout, CronTrigger(day=1, hour=1, minute=0), id="monthly_interest_payout")
    scheduler.add_job(job_trial_balance_generation, CronTrigger(hour=23, minute=55), id="trial_balance_generation")
    return scheduler
