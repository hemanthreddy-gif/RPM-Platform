"""Restrict conversations to exact participants with active monitoring consent.

Revision ID: 0016_conversation_participants
Revises: 0015_physician_onboarding
"""

from alembic import op

revision = "0016_conversation_participants"
down_revision = "0015_physician_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
      CREATE FUNCTION can_access_conversation(patient uuid, physician uuid, relationship uuid)
      RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER
      SET search_path = pg_catalog, public AS $$
        SELECT EXISTS (
          SELECT 1 FROM public.care_relationships r
          JOIN public.consents c ON c.id = r.consent_id AND c.patient_id = r.patient_id
          JOIN public.patients p ON p.id = r.patient_id
          JOIN public.physicians ph ON ph.id = r.physician_id
          WHERE r.id = relationship AND r.patient_id = patient AND r.physician_id = physician
            AND r.status = 'active' AND r.ended_at IS NULL
            AND c.purpose = 'monitoring' AND c.revoked_at IS NULL
            AND ((current_rpm_role() = 'patient' AND p.user_id = current_rpm_user_id())
              OR (current_rpm_role() = 'physician' AND ph.user_id = current_rpm_user_id()))
        )
      $$;
      REVOKE ALL ON FUNCTION can_access_conversation(uuid, uuid, uuid) FROM PUBLIC;
      GRANT EXECUTE ON FUNCTION can_access_conversation(uuid, uuid, uuid) TO rpm_runtime;
      DROP POLICY message_threads_read_policy ON message_threads;
      DROP POLICY message_threads_create_policy ON message_threads;
      CREATE POLICY message_threads_read_policy ON message_threads FOR SELECT USING (
        closed_at IS NULL AND can_access_conversation(patient_id, physician_id, relationship_id)
      );
      CREATE POLICY message_threads_create_policy ON message_threads FOR INSERT WITH CHECK (
        closed_at IS NULL AND can_access_conversation(patient_id, physician_id, relationship_id)
      );
    """)


def downgrade() -> None:
    op.execute("""
      DROP POLICY message_threads_read_policy ON message_threads;
      DROP POLICY message_threads_create_policy ON message_threads;
      CREATE POLICY message_threads_read_policy ON message_threads FOR SELECT USING (
        can_access_patient(patient_id, 'monitoring')
      );
      CREATE POLICY message_threads_create_policy ON message_threads FOR INSERT WITH CHECK (
        can_access_patient(patient_id, 'monitoring')
        AND EXISTS (SELECT 1 FROM physicians p WHERE p.id = physician_id)
      );
      DROP FUNCTION can_access_conversation(uuid, uuid, uuid);
    """)
