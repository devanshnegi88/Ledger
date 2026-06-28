"""
src/services/account_service.py

Design correction (documented in docs/submission-notes.md):

The spec's worked P2P example (Part A1.3, page 5) debits/credits accounts
named "1001-A" / "1001-B" as if they were Asset-side wallets, but its own
numbers don't balance (Debit 5,000 vs Credit 5,010 + 10). This is one of
the project's deliberate planted errors (per Section E5).

The technically correct model: 1001 (Customer Wallet — Asset) is the bank's
POOLED reserve account representing total cash held on behalf of all
customers. An individual customer's spendable balance is a LIABILITY
sub-account under 2001 (Customer Deposit Liability) — one row per customer
in `accounts`, sub_type="Customer Deposit Liability", normal_balance=CREDIT.

This keeps every customer-facing transaction (P2P, withdrawal, fee
deduction) balanced without inventing extra clearing accounts, and matches
real-world ledger design (each customer's "wallet" is the bank's liability
to them, not a bank asset).
"""
import uuid
from uuid6 import uuid7
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account, AccountType, NormalBalance

CUSTOMER_LIABILITY_PARENT_CODE = "2001"
POOLED_ASSET_CODE_BY_CURRENCY = {
    "INR": "1001",
    "USD": "1002",
    "EUR": "1003",
}


def customer_wallet_account_code(customer_ref: str, currency: str) -> str:
    return f"2001:{customer_ref}:{currency}"


def get_or_create_customer_wallet(db: Session, customer_ref: str, currency: str) -> Account:
    """
    Fetch the customer's wallet (Liability sub-account); create it on first
    use. customer_ref is an opaque external identifier (user ID, account
    number) supplied by the caller — NOT the literal Chart-of-Accounts code.
    """
    code = customer_wallet_account_code(customer_ref, currency)
    account = db.execute(
        select(Account).where(Account.account_code == code)
    ).scalar_one_or_none()
    if account is not None:
        return account

    account = Account(
        id=uuid7(),
        account_code=code,
        account_name=f"Customer Wallet ({customer_ref}, {currency})",
        account_type=AccountType.LIABILITY,
        sub_type="Customer Deposit Liability",
        currency=currency,
        normal_balance=NormalBalance.CREDIT,
        is_active=True,
        is_contra=False,
    )
    db.add(account)
    db.flush()
    return account


def fx_holding_account_code(currency: str) -> str:
    return f"FXHOLD:{currency}"


def get_or_create_fx_holding_account(db: Session, currency: str) -> Account:
    """
    Asset-side clearing account used as the intermediate leg of a
    multi-currency FX conversion journal (Part A3.2). One per currency.
    """
    code = fx_holding_account_code(currency)
    account = db.execute(
        select(Account).where(Account.account_code == code)
    ).scalar_one_or_none()
    if account is not None:
        return account

    account = Account(
        id=uuid7(),
        account_code=code,
        account_name=f"FX Conversion Holding ({currency})",
        account_type=AccountType.ASSET,
        sub_type="FX Conversion Holding",
        currency=currency,
        normal_balance=NormalBalance.DEBIT,
        is_active=True,
        is_contra=False,
    )
    db.add(account)
    db.flush()
    return account


def get_pooled_asset_account_code(currency: str) -> str:
    try:
        return POOLED_ASSET_CODE_BY_CURRENCY[currency]
    except KeyError:
        raise ValueError(f"No pooled asset account configured for currency '{currency}'")
