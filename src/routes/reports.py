"""
src/routes/reports.py
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query

from src.controllers.reporting_controller import (
    handle_trial_balance, handle_account_statement, handle_income_statement,
    handle_balance_sheet, handle_currency_exposure,
)

router = APIRouter(tags=["reports"])


@router.get("/api/v1/trial-balance")
def trial_balance(as_of_date: Optional[datetime] = Query(default=None)):
    return handle_trial_balance(as_of_date)


@router.get("/api/v1/accounts/{account_code}/statement")
def account_statement(
    account_code: str,
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    format: str = Query(default="json", pattern="^(json|csv)$"),
):
    return handle_account_statement(account_code, from_date, to_date, limit, offset, format)


@router.get("/api/v1/reports/income-statement")
def income_statement(
    from_date: Optional[datetime] = Query(default=None),
    to_date: Optional[datetime] = Query(default=None),
):
    return handle_income_statement(from_date, to_date)


@router.get("/api/v1/reports/balance-sheet")
def balance_sheet(as_of_date: Optional[datetime] = Query(default=None)):
    return handle_balance_sheet(as_of_date)


@router.get("/api/v1/reports/currency-exposure")
def currency_exposure():
    return handle_currency_exposure()
