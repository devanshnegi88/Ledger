"""008 create hash_chain_state singleton table

Revision ID: 008
Revises: 007
Create Date: 2026-06-20

A single-row table tracking the tip of the global ledger hash chain.
Appends acquire SELECT ... FOR UPDATE on this row to serialise concurrent
journal postings without locking the entire ledger_entries table.
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hash_chain_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("last_hash", sa.String(64), nullable=False),
        sa.Column("last_entry_id", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(f"INSERT INTO hash_chain_state (id, last_hash) VALUES (1, '{'0' * 64}');")


def downgrade() -> None:
    op.drop_table("hash_chain_state")
