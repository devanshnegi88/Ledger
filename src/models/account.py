"""
Chart of Accounts model.
Account types follow the fundamental accounting equation:
Assets = Liabilities + Equity, with Revenue/Expense flowing into Equity (Retained Earnings).
"""
import enum
import uuid
from uuid6 import uuid7
from sqlalchemy import Column, String, Boolean, DateTime, Enum, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from src.config.database import Base


class AccountType(str, enum.Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class NormalBalance(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


# Account types whose normal balance increases with a DEBIT.
DEBIT_NORMAL_TYPES = {AccountType.ASSET, AccountType.EXPENSE}
# Account types whose normal balance increases with a CREDIT.
CREDIT_NORMAL_TYPES = {AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE}


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    account_code = Column(String(10), unique=True, nullable=False, index=True)
    account_name = Column(String(150), nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    sub_type = Column(String(50), nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    normal_balance = Column(Enum(NormalBalance), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_contra = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("char_length(currency) = 3", name="ck_accounts_currency_iso4217"),
    )

    def __repr__(self) -> str:
        return f"<Account {self.account_code} {self.account_name} ({self.account_type})>"
