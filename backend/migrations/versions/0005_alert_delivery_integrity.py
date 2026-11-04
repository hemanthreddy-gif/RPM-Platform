"""Make Phase 4 delivery state unique and permit scoped worker reads.

Revision ID: 0005_alert_delivery_integrity
Revises: 0004_alert_worker_rls
"""

from alembic import op

revision = "0005_alert_delivery_integrity"
down_revision = "0004_alert_worker_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DROP POLICY patients_read_policy ON patients;
    CREATE POLICY patients_read_policy ON patients FOR SELECT USING (
      current_rpm_role() = 'worker'
      OR (current_rpm_role() = 'patient' AND user_id = current_rpm_user_id())
      OR (current_rpm_role() = 'physician' AND can_access_patient(id, 'monitoring'))
    );
    CREATE UNIQUE INDEX uq_notification_deliveries_alert_channel
      ON notification_deliveries (alert_id, channel);
    CREATE UNIQUE INDEX uq_job_attempts_outbox_event ON job_attempts (outbox_event_id);
    CREATE INDEX ix_alerts_patient_rule_created_open
      ON alerts (patient_id, rule_code, created_at DESC) WHERE status <> 'resolved';
    CREATE INDEX ix_outbox_alert_delivery_pending
      ON outbox_events (created_at) WHERE event_type = 'AlertNotificationRequested' AND published_at IS NULL;
    """)


def downgrade() -> None:
    raise RuntimeError("Restore 0004_alert_worker_rls manually before downgrading this revision")
