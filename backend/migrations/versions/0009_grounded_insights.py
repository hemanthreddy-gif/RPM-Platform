"""Protect versioned grounded-summary artifacts.

Revision ID: 0009_grounded_insights
Revises: 0008_meal_photo_comment_grants
"""

from alembic import op

revision = "0009_grounded_insights"
down_revision = "0008_meal_photo_comment_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE ai_artifacts ADD COLUMN supersedes_id uuid REFERENCES ai_artifacts(id);
    ALTER TABLE ai_artifacts ADD COLUMN created_by uuid REFERENCES users(id);
    ALTER TABLE ai_artifacts ADD COLUMN reviewed_at timestamptz;
    ALTER TABLE ai_artifacts ADD COLUMN approval_invalidated_at timestamptz;
    CREATE INDEX ix_ai_artifacts_patient_kind_created ON ai_artifacts (patient_id, kind, created_at DESC);

    ALTER TABLE ai_artifacts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE ai_artifacts FORCE ROW LEVEL SECURITY;
    CREATE POLICY ai_artifacts_read_policy ON ai_artifacts FOR SELECT USING (
      can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY ai_artifacts_physician_insert_policy ON ai_artifacts FOR INSERT WITH CHECK (
      current_rpm_role() = 'physician' AND created_by = current_rpm_user_id()
      AND can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY ai_artifacts_physician_review_policy ON ai_artifacts FOR UPDATE
      USING (current_rpm_role() = 'physician' AND can_access_patient(patient_id, 'monitoring'))
      WITH CHECK (current_rpm_role() = 'physician' AND can_access_patient(patient_id, 'monitoring'));
    GRANT SELECT, INSERT, UPDATE ON ai_artifacts TO rpm_runtime;

    CREATE FUNCTION enforce_ai_artifact_update() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'AI artifacts are retained for provenance';
      END IF;
      IF OLD.patient_id IS DISTINCT FROM NEW.patient_id OR OLD.kind IS DISTINCT FROM NEW.kind
        OR OLD.content IS DISTINCT FROM NEW.content OR OLD.model IS DISTINCT FROM NEW.model
        OR OLD.prompt_version IS DISTINCT FROM NEW.prompt_version OR OLD.input_refs IS DISTINCT FROM NEW.input_refs
        OR OLD.provider IS DISTINCT FROM NEW.provider OR OLD.schema_version IS DISTINCT FROM NEW.schema_version
        OR OLD.artifact_version IS DISTINCT FROM NEW.artifact_version OR OLD.supersedes_id IS DISTINCT FROM NEW.supersedes_id
        OR OLD.created_by IS DISTINCT FROM NEW.created_by OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'AI artifact content is immutable; create a new version';
      END IF;
      IF OLD.approval_invalidated_at IS DISTINCT FROM NEW.approval_invalidated_at THEN
        IF current_rpm_role() <> 'physician' OR OLD.status <> 'approved' THEN
          RAISE EXCEPTION 'only an approved artifact may have its approval invalidated';
        END IF;
        RETURN NEW;
      END IF;
      IF current_rpm_role() <> 'physician' OR NEW.reviewed_by IS DISTINCT FROM current_rpm_user_id()
        OR NEW.status NOT IN ('approved', 'rejected') THEN
        RAISE EXCEPTION 'only an authorized physician may review an artifact';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER ai_artifacts_write_guard BEFORE UPDATE OR DELETE ON ai_artifacts
      FOR EACH ROW EXECUTE FUNCTION enforce_ai_artifact_update();
    """)


def downgrade() -> None:
    raise RuntimeError("Restore 0008_meal_photo_comment_grants manually before downgrading")
