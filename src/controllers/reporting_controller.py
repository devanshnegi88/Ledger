"""
src/controllers/reporting_controller.py
"""
from typing import Optional
from datetime import datetime

from fastapi.responses import PlainTextResponse

from src.config.database import db_transaction
from src.services.trial_balance_service import generate_trial_balance
from src.services.reporting_service import (
    generate_account_statement, export_statement_csv,
    generate_income_statement, generate_balance_sheet, generate_currency_exposure_report,
)


def handle_trial_balance(as_of_date: Optional[datetime] = None) -> dict:
    with db_transaction() as db:
        report = generate_trial_balance(db, as_of_date)
        return {
            "as_of_date": report.as_of_date.isoformat() if report.as_of_date else None,
            "is_balanced": report.is_balanced,
            "total_debits": str(report.total_debits),
            "total_credits": str(report.total_credits),
            "rows": [
                {
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "account_type": r.account_type,
                    "total_debits": str(r.total_debits),
                    "total_credits": str(r.total_credits),
                    "net_balance": str(r.net_balance),
                }
                for r in report.rows
            ],
        }


def handle_account_statement(account_code: str, from_date: Optional[datetime], to_date: Optional[datetime],
                              limit: int, offset: int, export_format: str = "json"):
    with db_transaction() as db:
        lines = generate_account_statement(db, account_code, from_date=from_date, to_date=to_date, limit=limit, offset=offset)
        if export_format == "csv":
            return PlainTextResponse(export_statement_csv(lines), media_type="text/csv")
        return {
            "account_code": account_code,
            "count": len(lines),
            "lines": [
                {
                    "entry_id": l.entry_id, "effective_date": l.effective_date.isoformat(),
                    "entry_type": l.entry_type, "amount": str(l.amount),
                    "running_balance": str(l.running_balance), "narrative": l.narrative,
                    "reference_type": l.reference_type,
                }
                for l in lines
            ],
        }


def handle_income_statement(from_date: Optional[datetime], to_date: Optional[datetime]) -> dict:
    with db_transaction() as db:
        stmt = generate_income_statement(db, from_date=from_date, to_date=to_date)
        return {
            "period_from": stmt.period_from.isoformat() if stmt.period_from else None,
            "period_to": stmt.period_to.isoformat() if stmt.period_to else None,
            "total_revenue": str(stmt.total_revenue),
            "total_expense": str(stmt.total_expense),
            "net_income": str(stmt.net_income),
        }


def handle_balance_sheet(as_of_date: Optional[datetime]) -> dict:
    with db_transaction() as db:
        sheet = generate_balance_sheet(db, as_of_date=as_of_date)
        return {
            "as_of_date": as_of_date.isoformat() if as_of_date else None,
            "total_assets": str(sheet.total_assets),
            "total_liabilities": str(sheet.total_liabilities),
            "total_equity": str(sheet.total_equity),
            "is_balanced": sheet.is_balanced,
        }


def handle_currency_exposure() -> dict:
    with db_transaction() as db:
        rows = generate_currency_exposure_report(db)
        return {
            "rows": [
                {"currency": r.currency, "total_balance": str(r.total_balance), "inr_equivalent": str(r.inr_equivalent)}
                for r in rows
            ]
        }
