"""One-time trusted invitations and limited physician MFA bootstrap.

Revision ID: 0015_physician_onboarding
Revises: 0014_patient_profile_sleep
"""

from alembic import op

revision = "0015_physician_onboarding"
down_revision = "0014_patient_profile_sleep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
      ALTER TABLE physicians ADD COLUMN display_name text;
      CREATE TABLE physician_invitations (
        id uuid PRIMARY KEY,
        email text NOT NULL,
        display_name text NOT NULL,
        registration_no text NOT NULL,
        specialty text,
        token_hash text NOT NULL UNIQUE,
        expires_at timestamptz NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        created_by uuid REFERENCES users(id),
        started_at timestamptz,
        completed_at timestamptz,
        enrollment_hash text UNIQUE,
        enrollment_expires_at timestamptz,
        password_hash text,
        encrypted_secret text,
        failed_attempts integer NOT NULL DEFAULT 0 CHECK (failed_attempts BETWEEN 0 AND 5)
      );
      CREATE INDEX physician_invitations_email ON physician_invitations (lower(email));
      GRANT SELECT, INSERT, UPDATE ON physician_invitations TO rpm_runtime;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE physician_invitations")
    op.execute("ALTER TABLE physicians DROP COLUMN display_name")
