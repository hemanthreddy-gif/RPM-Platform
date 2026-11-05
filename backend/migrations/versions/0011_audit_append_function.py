"""Allow the sole audit service to append through a constrained database function.

Revision ID: 0011_audit_append
Revises: 0010_phase9_interop
"""

from alembic import op

revision = "0011_audit_append"
down_revision = "0010_phase9_interop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE FUNCTION record_audit_event(
      audit_actor_id uuid, audit_actor_role user_role, audit_action text,
      audit_resource_type text, audit_resource_id uuid, audit_patient_id uuid, audit_ip inet
    ) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
    BEGIN
      INSERT INTO public.audit_log (actor_id, actor_role, action, resource_type, resource_id, patient_id, ip)
      VALUES (audit_actor_id, audit_actor_role, audit_action, audit_resource_type,
              audit_resource_id, audit_patient_id, audit_ip);
    END $$;
    REVOKE ALL ON FUNCTION record_audit_event(uuid, user_role, text, text, uuid, uuid, inet) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION record_audit_event(uuid, user_role, text, text, uuid, uuid, inet) TO rpm_runtime;
    """)


def downgrade() -> None:
    raise RuntimeError("Restore 0010_phase9_interop manually before downgrading")
