"""Allow only trusted worker transactions to update alert delivery state.

Revision ID: 0004_alert_worker_rls
Revises: 0003_observation_target_rls
"""

from alembic import op

revision = "0004_alert_worker_rls"
down_revision = "0003_observation_target_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION can_access_patient(target_patient uuid, requested_purpose text)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT current_rpm_role() = 'worker'
      OR (current_rpm_role() = 'patient'
          AND target_patient = NULLIF(current_setting('app.patient_id', true), '')::uuid)
      OR (current_rpm_role() = 'physician' AND EXISTS (
        SELECT 1 FROM public.care_relationships cr
        JOIN public.physicians ph ON ph.id = cr.physician_id
        JOIN public.consents c ON c.id = cr.consent_id
        WHERE cr.patient_id = target_patient AND ph.user_id = current_rpm_user_id()
          AND cr.status = 'active' AND cr.ended_at IS NULL
          AND c.revoked_at IS NULL AND c.purpose = requested_purpose
      ))
    $$;
    """)


def downgrade() -> None:
    raise RuntimeError("Restore 0002_identity_security manually before downgrading this revision")
