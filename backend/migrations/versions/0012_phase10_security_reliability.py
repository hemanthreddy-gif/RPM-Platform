"""Add access-token invalidation epoch for Phase 10 hardening.

Revision ID: 0012_phase10_security
Revises: 0011_audit_append
"""

from alembic import op

revision = "0012_phase10_security"
down_revision = "0011_audit_append"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN token_valid_after timestamptz NOT NULL DEFAULT 'epoch'::timestamptz;"
    )


def downgrade() -> None:
    raise RuntimeError("Restore 0011_audit_append manually before downgrading")
