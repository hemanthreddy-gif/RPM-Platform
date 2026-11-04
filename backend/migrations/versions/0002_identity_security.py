"""Add Phase 2 identity fields and database access-control boundaries.

Revision ID: 0002_identity_security
Revises: 0001_initial_schema
"""

from alembic import op

revision = "0002_identity_security"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE users ADD COLUMN password_hash text;
    ALTER TABLE users ADD COLUMN failed_login_attempts integer NOT NULL DEFAULT 0;
    ALTER TABLE users ADD COLUMN locked_until timestamptz;
    ALTER TABLE identity_tokens ADD COLUMN replaced_by uuid REFERENCES identity_tokens(id);
    CREATE INDEX ix_identity_tokens_user_type ON identity_tokens(user_id, token_type);

    CREATE FUNCTION current_rpm_user_id() RETURNS uuid LANGUAGE sql STABLE AS $$
      SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
    $$;
    CREATE FUNCTION current_rpm_role() RETURNS text LANGUAGE sql STABLE AS $$
      SELECT NULLIF(current_setting('app.role', true), '')
    $$;
    CREATE FUNCTION can_access_patient(target_patient uuid, requested_purpose text)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT current_rpm_role() = 'patient'
             AND target_patient = NULLIF(current_setting('app.patient_id', true), '')::uuid
      OR (
        current_rpm_role() = 'physician'
        AND EXISTS (
          SELECT 1 FROM public.care_relationships cr
          JOIN public.physicians ph ON ph.id = cr.physician_id
          JOIN public.consents c ON c.id = cr.consent_id
          WHERE cr.patient_id = target_patient AND ph.user_id = current_rpm_user_id()
            AND cr.status = 'active' AND cr.ended_at IS NULL
            AND c.revoked_at IS NULL AND c.purpose = requested_purpose
        )
      )
    $$;

    ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
    ALTER TABLE patients FORCE ROW LEVEL SECURITY;
    CREATE POLICY patients_read_policy ON patients FOR SELECT USING (
      (current_rpm_role() = 'patient' AND user_id = current_rpm_user_id())
      OR (current_rpm_role() = 'physician' AND can_access_patient(id, 'monitoring'))
    );
    CREATE POLICY patients_update_policy ON patients FOR UPDATE USING (current_rpm_role() = 'patient' AND user_id = current_rpm_user_id());
    ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
    ALTER TABLE observations FORCE ROW LEVEL SECURITY;
    CREATE POLICY observations_patient_policy ON observations FOR ALL USING (can_access_patient(patient_id, 'monitoring')) WITH CHECK (can_access_patient(patient_id, 'monitoring'));
    ALTER TABLE meals ENABLE ROW LEVEL SECURITY;
    ALTER TABLE meals FORCE ROW LEVEL SECURITY;
    CREATE POLICY meals_patient_policy ON meals FOR ALL USING (can_access_patient(patient_id, 'monitoring')) WITH CHECK (can_access_patient(patient_id, 'monitoring'));
    ALTER TABLE medications ENABLE ROW LEVEL SECURITY;
    ALTER TABLE medications FORCE ROW LEVEL SECURITY;
    CREATE POLICY medications_patient_policy ON medications FOR ALL USING (can_access_patient(patient_id, 'monitoring')) WITH CHECK (can_access_patient(patient_id, 'monitoring'));
    ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE alerts FORCE ROW LEVEL SECURITY;
    CREATE POLICY alerts_patient_policy ON alerts FOR ALL USING (can_access_patient(patient_id, 'monitoring')) WITH CHECK (can_access_patient(patient_id, 'monitoring'));

    ALTER ROLE rpm_runtime NOBYPASSRLS;
    GRANT EXECUTE ON FUNCTION can_access_patient(uuid, text) TO rpm_runtime;
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS alerts_patient_policy ON alerts; ALTER TABLE alerts DISABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS medications_patient_policy ON medications; ALTER TABLE medications DISABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS meals_patient_policy ON meals; ALTER TABLE meals DISABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS observations_patient_policy ON observations; ALTER TABLE observations DISABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS patients_update_policy ON patients; DROP POLICY IF EXISTS patients_read_policy ON patients; ALTER TABLE patients DISABLE ROW LEVEL SECURITY;
    DROP FUNCTION IF EXISTS can_access_patient(uuid, text); DROP FUNCTION IF EXISTS current_rpm_role(); DROP FUNCTION IF EXISTS current_rpm_user_id();
    DROP INDEX IF EXISTS ix_identity_tokens_user_type;
    ALTER TABLE identity_tokens DROP COLUMN IF EXISTS replaced_by;
    ALTER TABLE users DROP COLUMN IF EXISTS locked_until;
    ALTER TABLE users DROP COLUMN IF EXISTS failed_login_attempts;
    ALTER TABLE users DROP COLUMN IF EXISTS password_hash;
    """)
