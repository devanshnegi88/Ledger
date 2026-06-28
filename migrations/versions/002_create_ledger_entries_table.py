"""002 create transactions journals ledger_entries tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="INITIATED"),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_payload", postgresql.JSONB, nullable=False),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_transactions_idempotency_key", "transactions", ["idempotency_key"])
    op.create_index("ix_transactions_type", "transactions", ["transaction_type"])
    op.create_index("ix_transactions_status", "transactions", ["status"])

    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journal_reference", sa.String(60), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("narrative", sa.String(500)),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB, server_default="{}"),
    )
    op.create_unique_constraint("uq_journals_reference", "journals", ["journal_reference"])

    op.create_table(
        "ledger_entries",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("journal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journals.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("entry_type", sa.Enum("DEBIT", "CREDIT", name="entrytype"), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=True),
        sa.Column("reference_type", sa.String(60), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("narrative", sa.String(500)),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, server_default="{}"),
        sa.Column(
            "status",
            sa.Enum("PENDING", "POSTED", "REVERSED", name="entrystatus"),
            nullable=False,
            server_default="POSTED",
        ),
        sa.CheckConstraint("amount > 0", name="ck_ledger_entries_amount_positive"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_ledger_entries_currency_iso4217"),
        sa.CheckConstraint("char_length(hash) = 64", name="ck_ledger_entries_hash_len"),
    )
    op.create_unique_constraint("uq_ledger_entries_idempotency_key", "ledger_entries", ["idempotency_key"])
    op.create_index("ix_ledger_entries_account_id", "ledger_entries", ["account_id"])
    op.create_index("ix_ledger_entries_journal_id", "ledger_entries", ["journal_id"])
    op.create_index("ix_ledger_entries_effective_date", "ledger_entries", ["effective_date"])
    op.create_index("ix_ledger_entries_reference_id", "ledger_entries", ["reference_id"])
    op.create_index(
        "ix_ledger_entries_account_effective",
        "ledger_entries",
        ["account_id", "effective_date"],
    )


def downgrade() -> None:
    op.drop_table("ledger_entries")
    op.execute("DROP TYPE IF EXISTS entrytype")
    op.execute("DROP TYPE IF EXISTS entrystatus")
    op.drop_table("journals")
    op.drop_table("transactions")
