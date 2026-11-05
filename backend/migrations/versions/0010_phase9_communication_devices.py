"""Add consent-scoped messaging and paired synthetic-device metadata.

Revision ID: 0010_phase9_interop
Revises: 0009_grounded_insights
"""

from alembic import op

revision = "0010_phase9_interop"
down_revision = "0009_grounded_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE devices ADD COLUMN pairing_token_hash text;
    ALTER TABLE devices ADD COLUMN paired_at timestamptz;
    ALTER TABLE devices ADD COLUMN last_received_at timestamptz;
    ALTER TABLE devices ADD COLUMN created_by uuid REFERENCES users(id);
    ALTER TABLE devices ADD CONSTRAINT ck_devices_status CHECK (status IN ('active', 'revoked'));
    CREATE UNIQUE INDEX uq_devices_patient_serial ON devices (patient_id, serial) WHERE serial IS NOT NULL;

    CREATE TABLE message_threads (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      physician_id uuid NOT NULL REFERENCES physicians(id), relationship_id uuid NOT NULL REFERENCES care_relationships(id),
      created_at timestamptz NOT NULL DEFAULT now(), closed_at timestamptz,
      UNIQUE(patient_id, physician_id, relationship_id)
    );
    ALTER TABLE messages ADD COLUMN kind text NOT NULL DEFAULT 'message';
    ALTER TABLE messages ADD CONSTRAINT ck_messages_kind CHECK (kind IN ('message', 'appointment_request'));
    CREATE INDEX ix_messages_thread_sent ON messages (thread_id, sent_at);

    ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
    ALTER TABLE devices FORCE ROW LEVEL SECURITY;
    CREATE POLICY devices_read_policy ON devices FOR SELECT USING (
      can_access_patient(patient_id, 'monitoring')
      OR (current_rpm_role() = 'device' AND id = NULLIF(current_setting('app.device_id', true), '')::uuid)
    );
    CREATE POLICY devices_patient_insert_policy ON devices FOR INSERT WITH CHECK (
      current_rpm_role() = 'patient' AND created_by = current_rpm_user_id()
      AND can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY devices_patient_update_policy ON devices FOR UPDATE USING (
      current_rpm_role() = 'patient' AND can_access_patient(patient_id, 'monitoring')
    ) WITH CHECK (current_rpm_role() = 'patient' AND can_access_patient(patient_id, 'monitoring'));

    ALTER TABLE message_threads ENABLE ROW LEVEL SECURITY;
    ALTER TABLE message_threads FORCE ROW LEVEL SECURITY;
    CREATE POLICY message_threads_read_policy ON message_threads FOR SELECT USING (
      can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY message_threads_create_policy ON message_threads FOR INSERT WITH CHECK (
      can_access_patient(patient_id, 'monitoring')
      AND EXISTS (SELECT 1 FROM physicians p WHERE p.id = physician_id)
    );
    ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
    ALTER TABLE messages FORCE ROW LEVEL SECURITY;
    CREATE POLICY messages_read_policy ON messages FOR SELECT USING (
      EXISTS (SELECT 1 FROM message_threads t WHERE t.id = thread_id
        AND can_access_patient(t.patient_id, 'monitoring'))
    );
    CREATE POLICY messages_create_policy ON messages FOR INSERT WITH CHECK (
      sender_id = current_rpm_user_id() AND EXISTS (
        SELECT 1 FROM message_threads t WHERE t.id = thread_id
          AND can_access_patient(t.patient_id, 'monitoring')
      )
    );
    CREATE POLICY messages_read_receipt_policy ON messages FOR UPDATE USING (
      recipient_id = current_rpm_user_id() AND EXISTS (
        SELECT 1 FROM message_threads t WHERE t.id = thread_id
          AND can_access_patient(t.patient_id, 'monitoring')
      )
    ) WITH CHECK (recipient_id = current_rpm_user_id());
    GRANT SELECT, INSERT, UPDATE ON devices, message_threads, messages TO rpm_runtime;
    """)


def downgrade() -> None:
    raise RuntimeError("Restore 0009_grounded_insights manually before downgrading")
