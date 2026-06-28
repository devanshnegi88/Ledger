"""
src/services/reporting_service.py

Part A6.2 / A6.3 — Reporting Suite. Day 12.
"""
import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account, AccountType, DEBIT_NORMAL_TYPES
from src.models.ledger_entry import LedgerEntry, EntryType, EntryStatus


@dataclass
class StatementLine:
    entry_id: str
    effective_date: datetime
    entry_type: str
    amount: Decimal
    running_balance: Decimal
    narrative: Optional[str]
    reference_type: str


def generate_account_statement(
    db: Session, account_code: str, *, from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None, limit: int = 100, offset: int = 0,
) -> List[StatementLine]:
    """Part A6.2 — transaction-level detail for one account with a running balance."""
    account = db.execute(select(Account).where(Account.account_code == account_code)).scalar_one()

    query = (
        select(LedgerEntry)
        .where(LedgerEntry.account_id == account.id, LedgerEntry.status == EntryStatus.POSTED)
        .order_by(LedgerEntry.effective_date, LedgerEntry.posted_at)
    )
    if from_date is not None:
        query = query.where(LedgerEntry.effective_date >= from_date)
    if to_date is not None:
        query = query.where(LedgerEntry.effective_date <= to_date)

    all_entries = list(db.execute(query).scalars().all())

    lines: List[StatementLine] = []
    running = Decimal("0.0000")
    debit_increases = account.account_type in DEBIT_NORMAL_TYPES

    for entry in all_entries:
        signed = entry.amount if (
            (entry.entry_type == EntryType.DEBIT) == debit_increases
        ) else -entry.amount
        running += signed
        lines.append(StatementLine(
            entry_id=str(entry.entry_id),
            effective_date=entry.effective_date,
            entry_type=entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type,
            amount=entry.amount,
            running_balance=running,
            narrative=entry.narrative,
            reference_type=entry.reference_type,
        ))

    return lines[offset: offset + limit]


def export_statement_csv(lines: List[StatementLine]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["entry_id", "effective_date", "entry_type", "amount", "running_balance", "narrative", "reference_type"])
    for line in lines:
        writer.writerow([
            line.entry_id, line.effective_date.isoformat(), line.entry_type,
            str(line.amount), str(line.running_balance), line.narrative or "", line.reference_type,
        ])
    return buf.getvalue()


@dataclass
class IncomeStatement:
    period_from: Optional[datetime]
    period_to: Optional[datetime]
    total_revenue: Decimal
    total_expense: Decimal

    @property
    def net_income(self) -> Decimal:
        return self.total_revenue - self.total_expense


def generate_income_statement(db: Session, *, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None) -> IncomeStatement:
    """Part A6.3 — Revenue minus Expenses for a period."""
    def _sum_for_type(account_type: AccountType) -> Decimal:
        query = (
            select(LedgerEntry.amount, LedgerEntry.entry_type)
            .join(Account, Account.id == LedgerEntry.account_id)
            .where(Account.account_type == account_type, LedgerEntry.status == EntryStatus.POSTED)
        )
        if from_date is not None:
            query = query.where(LedgerEntry.effective_date >= from_date)
        if to_date is not None:
            query = query.where(LedgerEntry.effective_date <= to_date)

        total = Decimal("0.0000")
        credit_normal = account_type not in DEBIT_NORMAL_TYPES
        for amount, entry_type in db.execute(query).all():
            amount = Decimal(amount)
            is_increase = (entry_type == EntryType.CREDIT) == credit_normal
            total += amount if is_increase else -amount
        return total

    return IncomeStatement(
        period_from=from_date, period_to=to_date,
        total_revenue=_sum_for_type(AccountType.REVENUE),
        total_expense=_sum_for_type(AccountType.EXPENSE),
    )


@dataclass
class BalanceSheet:
    as_of_date: Optional[datetime]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal

    @property
    def is_balanced(self) -> bool:
        return self.total_assets == (self.total_liabilities + self.total_equity)


def generate_balance_sheet(db: Session, *, as_of_date: Optional[datetime] = None) -> BalanceSheet:
    """Part A6.3 — Assets, Liabilities, Equity at a point in time. Must satisfy A = L + E."""
    from src.services.balance_service import compute_account_balance

    accounts = db.execute(select(Account)).scalars().all()
    totals = {AccountType.ASSET: Decimal("0"), AccountType.LIABILITY: Decimal("0"), AccountType.EQUITY: Decimal("0")}

    for account in accounts:
        if account.account_type not in totals:
            continue
        totals[account.account_type] += compute_account_balance(db, account.id)

    return BalanceSheet(
        as_of_date=as_of_date,
        total_assets=totals[AccountType.ASSET],
        total_liabilities=totals[AccountType.LIABILITY],
        total_equity=totals[AccountType.EQUITY],
    )


@dataclass
class CurrencyExposureRow:
    currency: str
    total_balance: Decimal
    inr_equivalent: Decimal


def generate_currency_exposure_report(db: Session) -> List[CurrencyExposureRow]:
    """Part A6.3 — total balances held in each currency, with INR-equivalent at current rates."""
    from src.services.balance_service import compute_account_balance
    from src.services.exchange_rate_service import get_latest_rate
    from src.utils.exceptions import StaleRateError

    accounts = db.execute(select(Account)).scalars().all()
    by_currency: dict = {}
    for account in accounts:
        balance = compute_account_balance(db, account.id)
        by_currency.setdefault(account.currency, Decimal("0"))
        by_currency[account.currency] += balance

    rows: List[CurrencyExposureRow] = []
    for currency, total in by_currency.items():
        if currency == "INR":
            inr_equivalent = total
        else:
            try:
                snapshot = get_latest_rate(db, currency, "INR")
                inr_equivalent = (total * snapshot.rate).quantize(Decimal("0.0001"))
            except StaleRateError:
                inr_equivalent = Decimal("0.0000")  # unresolvable — flagged as 0 rather than guessed
        rows.append(CurrencyExposureRow(currency=currency, total_balance=total, inr_equivalent=inr_equivalent))

    return rows
