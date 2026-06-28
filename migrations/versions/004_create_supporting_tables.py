"""004 create balance_snapshots exchange_rate_snapshots reversals audit_logs idempotency_keys

Revision ID: 004
Revises: 003
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "exchange_rate_snapshots",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("quote_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("inverse_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("rate > 0", name="ck_fx_rate_positive"),
        sa.CheckConstraint("inverse_rate > 0", name="ck_fx_inverse_rate_positive"),
    )
    op.create_index("ix_fx_base_quote", "exchange_rate_snapshots", ["base_currency", "quote_currency"])

    op.create_table(
        "reversals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("reversal_transaction_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("reversal_idempotency_key", sa.String(128), nullable=False),
        sa.Column("reversal_type", sa.Enum("FULL", "PARTIAL", name="reversaltype"), nullable=False),
        sa.Column("fee_refund_policy", sa.Enum("PROPORTIONAL", "FULL", "NONE", name="feerefundpolicy"), nullable=True),
        sa.Column("refunded_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint(
            "original_transaction_id", "reversal_idempotency_key",
            name="uq_reversal_original_idempotency",
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(60), nullable=True),
        sa.Column("details", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("endpoint", sa.String(150), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer, nullable=True),
        sa.Column("response_body", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PROCESSING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_idempotency_user_key_active", "idempotency_keys",
        ["user_id", "key"], unique=True,
        postgresql_where=sa.text("expires_at > now()"),
    )

    op.create_table(
        "balance_snapshots",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), primary_key=True),
        sa.Column("balance", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("last_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), onupdate=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("balance_snapshots")
    op.drop_table("idempotency_keys")
    op.drop_table("audit_logs")
    op.drop_table("reversals")
    op.execute("DROP TYPE IF EXISTS reversaltype")
    op.execute("DROP TYPE IF EXISTS feerefundpolicy")
    op.drop_table("exchange_rate_snapshots")
