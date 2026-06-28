"""
src/services/trial_balance_service.py

Trial balance generation (Part A6.1, Day 4).

NOTE — correction vs. the spec's reference query (Section A6.1): the
reference SQL computes `net_balance` as `DEBIT amount ELSE -amount`
unconditionally for every account, which is only correct for Asset/Expense
accounts. For Liability/Equity/Revenue accounts (normal balance CREDIT),
that formula reports the balance with an inverted sign. This service
applies the correct sign per `account.normal_balance` so a Liability
account with more credits than debits reports a positive balance.
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from src.models.account import Account, DEBIT_NORMAL_TYPES
from src.models.ledger_entry import LedgerEntry, EntryType, EntryStatus


@dataclass
class TrialBalanceRow:
    account_code: str
    account_name: str
    account_type: str
    total_debits: Decimal
    total_credits: Decimal
    net_balance: Decimal


@dataclass
class TrialBalanceReport:
    as_of_date: Optional[datetime]
    rows: List[TrialBalanceRow]
    total_debits: Decimal
    total_credits: Decimal

    @property
    def is_balanced(self) -> bool:
        return self.total_debits == self.total_credits


def generate_trial_balance(db: Session, as_of_date: Optional[datetime] = None) -> TrialBalanceReport:
    query = (
        select(
            Account.account_code,
            Account.account_name,
            Account.account_type,
            func.coalesce(
                func.sum(
                    func.case((LedgerEntry.entry_type == EntryType.DEBIT, LedgerEntry.amount), else_=0)
                ), 0
            ).label("total_debits"),
            func.coalesce(
                func.sum(
                    func.case((LedgerEntry.entry_type == EntryType.CREDIT, LedgerEntry.amount), else_=0)
                ), 0
            ).label("total_credits"),
        )
        .select_from(Account)
        .outerjoin(
            LedgerEntry,
            (LedgerEntry.account_id == Account.id) & (LedgerEntry.status == EntryStatus.POSTED),
        )
        .group_by(Account.id, Account.account_code, Account.account_name, Account.account_type)
        .order_by(Account.account_code)
    )

    if as_of_date is not None:
        query = query.where(
            (LedgerEntry.effective_date <= as_of_date) | (LedgerEntry.effective_date.is_(None))
        )

    results = db.execute(query).all()

    rows: List[TrialBalanceRow] = []
    total_debits = Decimal("0.0000")
    total_credits = Decimal("0.0000")

    for code, name, acc_type, debits, credits in results:
        debits = Decimal(debits)
        credits = Decimal(credits)
        total_debits += debits
        total_credits += credits

        if acc_type in DEBIT_NORMAL_TYPES:
            net = debits - credits
        else:
            net = credits - debits

        rows.append(TrialBalanceRow(
            account_code=code,
            account_name=name,
            account_type=acc_type.value if hasattr(acc_type, "value") else acc_type,
            total_debits=debits,
            total_credits=credits,
            net_balance=net,
        ))

    return TrialBalanceReport(
        as_of_date=as_of_date,
        rows=rows,
        total_debits=total_debits,
        total_credits=total_credits,
    )
