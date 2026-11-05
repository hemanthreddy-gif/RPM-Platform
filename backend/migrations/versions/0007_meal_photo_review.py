"""Add private meal-photo metadata and append-only physician review comments.

Revision ID: 0007_meal_photo_review
Revises: 0006_medication_adherence
"""

from alembic import op

revision = "0007_meal_photo_review"
down_revision = "0006_medication_adherence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TYPE meal_status ADD VALUE IF NOT EXISTS 'submitted';
    ALTER TABLE meals ADD COLUMN uploaded_at timestamptz;
    ALTER TABLE meals ADD COLUMN image_sha256 text;
    ALTER TABLE meals ADD COLUMN image_content_type text;
    ALTER TABLE meals ADD COLUMN image_size_bytes integer;
    ALTER TABLE meals ADD CONSTRAINT ck_meals_image_metadata CHECK (
      (image_key IS NULL AND image_sha256 IS NULL AND image_content_type IS NULL AND image_size_bytes IS NULL)
      OR (image_key IS NOT NULL AND image_sha256 ~ '^[0-9a-f]{64}$'
          AND image_content_type = 'image/jpeg' AND image_size_bytes > 0)
    );
    CREATE INDEX ix_meals_patient_uploaded_at ON meals (patient_id, uploaded_at DESC);

    CREATE TABLE meal_photo_comments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      meal_id uuid NOT NULL REFERENCES meals(id),
      author_id uuid NOT NULL REFERENCES users(id),
      body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 1000),
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_meal_photo_comments_meal_created ON meal_photo_comments (meal_id, created_at);
    CREATE FUNCTION prevent_meal_photo_comment_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'meal photo comments are append-only'; END; $$;
    CREATE TRIGGER meal_photo_comments_append_only BEFORE UPDATE OR DELETE ON meal_photo_comments
      FOR EACH ROW EXECUTE FUNCTION prevent_meal_photo_comment_mutation();

    DROP POLICY IF EXISTS meals_patient_policy ON meals;
    CREATE POLICY meals_read_policy ON meals FOR SELECT USING (can_access_patient(patient_id, 'monitoring'));
    CREATE POLICY meals_patient_insert_policy ON meals FOR INSERT WITH CHECK (
      current_rpm_role() = 'patient' AND can_access_patient(patient_id, 'monitoring')
    );

    ALTER TABLE meal_photo_comments ENABLE ROW LEVEL SECURITY;
    ALTER TABLE meal_photo_comments FORCE ROW LEVEL SECURITY;
    CREATE POLICY meal_photo_comments_read_policy ON meal_photo_comments FOR SELECT USING (
      EXISTS (SELECT 1 FROM meals m WHERE m.id = meal_id AND can_access_patient(m.patient_id, 'monitoring'))
    );
    CREATE POLICY meal_photo_comments_physician_insert_policy ON meal_photo_comments FOR INSERT WITH CHECK (
      current_rpm_role() = 'physician' AND author_id = current_rpm_user_id()
      AND EXISTS (SELECT 1 FROM meals m WHERE m.id = meal_id AND can_access_patient(m.patient_id, 'monitoring'))
    );
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS meal_photo_comments_physician_insert_policy ON meal_photo_comments;
    DROP POLICY IF EXISTS meal_photo_comments_read_policy ON meal_photo_comments;
    ALTER TABLE meal_photo_comments DISABLE ROW LEVEL SECURITY;
    DROP TRIGGER IF EXISTS meal_photo_comments_append_only ON meal_photo_comments;
    DROP FUNCTION IF EXISTS prevent_meal_photo_comment_mutation();
    DROP TABLE IF EXISTS meal_photo_comments;
    DROP POLICY IF EXISTS meals_patient_insert_policy ON meals;
    DROP POLICY IF EXISTS meals_read_policy ON meals;
    CREATE POLICY meals_patient_policy ON meals FOR ALL USING (can_access_patient(patient_id, 'monitoring')) WITH CHECK (can_access_patient(patient_id, 'monitoring'));
    ALTER TABLE meals DROP CONSTRAINT IF EXISTS ck_meals_image_metadata;
    ALTER TABLE meals DROP COLUMN IF EXISTS image_size_bytes;
    ALTER TABLE meals DROP COLUMN IF EXISTS image_content_type;
    ALTER TABLE meals DROP COLUMN IF EXISTS image_sha256;
    ALTER TABLE meals DROP COLUMN IF EXISTS uploaded_at;
    DROP INDEX IF EXISTS ix_meals_patient_uploaded_at;
    """)
