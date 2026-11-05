"""Grant the runtime role the minimal meal-photo-comment privileges.

Revision ID: 0008_meal_photo_comment_grants
Revises: 0007_meal_photo_review
"""

from alembic import op

revision = "0008_meal_photo_comment_grants"
down_revision = "0007_meal_photo_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS remains the authorization authority.  The explicit grants only let the constrained
    # runtime role reach policies for the two operations the API needs.
    op.execute("GRANT SELECT, INSERT ON meal_photo_comments TO rpm_runtime")


def downgrade() -> None:
    op.execute("REVOKE SELECT, INSERT ON meal_photo_comments FROM rpm_runtime")
