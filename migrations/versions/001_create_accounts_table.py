"""001 create accounts table

Revision ID: 001
Revises:
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_code", sa.String(10), nullable=False),
        sa.Column("account_name", sa.String(150), nullable=False),
        sa.Column(
            "account_type",
            sa.Enum("ASSET", "LIABILITY", "EQUITY", "REVENUE", "EXPENSE", name="accounttype"),
            nullable=False,
        ),
        sa.Column("sub_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column(
            "normal_balance",
            sa.Enum("DEBIT", "CREDIT", name="normalbalance"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_contra", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_accounts_currency_iso4217"),
    )
    op.create_unique_constraint("uq_accounts_account_code", "accounts", ["account_code"])
    op.create_index("ix_accounts_account_code", "accounts", ["account_code"])


def downgrade() -> None:
    op.drop_index("ix_accounts_account_code", table_name="accounts")
    op.drop_table("accounts")
    op.execute("DROP TYPE IF EXISTS accounttype")
    op.execute("DROP TYPE IF EXISTS normalbalance")
