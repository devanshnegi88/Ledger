"""003 create immutability triggers on ledger_entries

Revision ID: 003
Revises: 002
Create Date: 2026-06-20

Implements Part A2.2 "Database Triggers" strategy: BEFORE UPDATE/DELETE
triggers raise exceptions on any ledger_entries row, regardless of status.
Combined with the append-only application design, this gives defence in
depth against accidental or malicious mutation of posted financial records.

The ONLY sanctioned mutation is a status transition POSTED -> REVERSED,
which we allow narrowly (status column only, via the reversal service);
everything else (amount, hash, account_id, etc.) is blocked unconditionally.
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

TRIGGER_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION fn_prevent_ledger_entry_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: ledger_entries rows cannot be deleted (entry_id=%). Use a reversal entry instead.',
            OLD.entry_id;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Allow ONLY a status transition from POSTED to REVERSED; nothing else may change.
        IF OLD.status = 'POSTED' AND NEW.status = 'REVERSED'
           AND NEW.entry_id = OLD.entry_id
           AND NEW.journal_id = OLD.journal_id
           AND NEW.account_id = OLD.account_id
           AND NEW.entry_type = OLD.entry_type
           AND NEW.amount = OLD.amount
           AND NEW.currency = OLD.currency
           AND NEW.effective_date = OLD.effective_date
           AND NEW.hash = OLD.hash
           AND NEW.previous_hash = OLD.previous_hash
        THEN
            RETURN NEW;
        END IF;

        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: ledger_entries row (entry_id=%) cannot be mutated. Create a reversal entry instead.',
            OLD.entry_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

TRIGGER_SQL = """
CREATE TRIGGER trg_prevent_ledger_entry_update
BEFORE UPDATE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION fn_prevent_ledger_entry_mutation();

CREATE TRIGGER trg_prevent_ledger_entry_delete
BEFORE DELETE ON ledger_entries
FOR EACH ROW EXECUTE FUNCTION fn_prevent_ledger_entry_mutation();
"""


def upgrade() -> None:
    op.execute(TRIGGER_FUNCTION_SQL)
    op.execute(TRIGGER_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_ledger_entry_update ON ledger_entries;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_ledger_entry_delete ON ledger_entries;")
    op.execute("DROP FUNCTION IF EXISTS fn_prevent_ledger_entry_mutation();")
