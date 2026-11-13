"""Private patient profiles and self-reported sleep observations.

Revision ID: 0014_patient_profile_sleep
Revises: 0013_bp_components
"""

from alembic import op

revision = "0014_patient_profile_sleep"
down_revision = "0013_bp_components"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New labels cannot be used until commit; the following DDL does not use the label.
    op.execute("ALTER TYPE observation_type ADD VALUE IF NOT EXISTS 'sleep'")
    op.execute("""
      ALTER TABLE patients ADD COLUMN gender text;
      ALTER TABLE patients ADD COLUMN phone text;
      ALTER TABLE patients ADD COLUMN height_cm numeric CHECK (height_cm > 0 AND height_cm <= 300);
      ALTER TABLE patients ADD COLUMN weight_kg numeric CHECK (weight_kg > 0 AND weight_kg <= 700);
      ALTER TABLE patients ADD COLUMN profile_picture bytea
        CHECK (octet_length(profile_picture) <= 2097152);
      ALTER TABLE patients ADD COLUMN profile_picture_updated_at timestamptz;
    """)


def downgrade() -> None:
    # Keep an unused enum label: PostgreSQL cannot remove one safely while immutable history
    # references it. Refuse to discard user-created profile data on a downgrade.
    op.execute("""
      DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM patients WHERE gender IS NOT NULL OR phone IS NOT NULL
          OR height_cm IS NOT NULL OR weight_kg IS NOT NULL OR profile_picture IS NOT NULL)
        THEN RAISE EXCEPTION 'Patient profile data exists; restore from a backup to downgrade';
        END IF;
      END $$;
      ALTER TABLE patients DROP COLUMN profile_picture_updated_at;
      ALTER TABLE patients DROP COLUMN profile_picture;
      ALTER TABLE patients DROP COLUMN weight_kg;
      ALTER TABLE patients DROP COLUMN height_cm;
      ALTER TABLE patients DROP COLUMN phone;
      ALTER TABLE patients DROP COLUMN gender;
    """)
