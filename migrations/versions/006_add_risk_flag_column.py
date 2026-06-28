"""006 add risk_flag column to accounts (non-blocking ADD COLUMN)

Revision ID: 006
Revises: 005
Create Date: 2026-06-20

ALTER TABLE ... ADD COLUMN with a constant default and nullable=True is
non-blocking in PostgreSQL 11+ (no full table rewrite). Avoid
ALTER TABLE ... ALTER TYPE elsewhere, per Part A7.3.
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("risk_flag", sa.Boolean(), nullable=True, server_default="false"))


def downgrade() -> None:
    op.drop_column("accounts", "risk_flag")
