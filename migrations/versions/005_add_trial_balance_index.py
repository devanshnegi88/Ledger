"""005 add covering index for trial balance queries (zero-downtime demo)

Revision ID: 005
Revises: 004
Create Date: 2026-06-20

Demonstrates a zero-downtime schema change (Part A7.3 / Day 14): index
creation that does not block reads/writes on ledger_entries.
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    # autocommit_block() suspends Alembic's transactional DDL wrapping for
    # just this operation, so the rest of the migration chain remains
    # transactional as normal.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_ledger_entries_status_account "
            "ON ledger_entries (status, account_id);"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_ledger_entries_status_account;")
