"""Allow component-only blood-pressure records without inventing a scalar value.

Revision ID: 0013_bp_components
Revises: 0012_phase10_security
"""

from alembic import op

revision = "0013_bp_components"
down_revision = "0012_phase10_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE observations ALTER COLUMN original_value DROP NOT NULL")
    op.execute(
        "ALTER TABLE observations ADD CONSTRAINT observations_scalar_original_required "
        "CHECK (type = 'blood_pressure' OR original_value IS NOT NULL)"
    )


def downgrade() -> None:
    # PostgreSQL rejects this operation if component-only readings exist; never discard them.
    op.execute("ALTER TABLE observations DROP CONSTRAINT observations_scalar_original_required")
    op.execute("ALTER TABLE observations ALTER COLUMN original_value SET NOT NULL")
