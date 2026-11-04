"""Add protected synthetic medication scheduling and self-report provenance.

Revision ID: 0006_medication_adherence
Revises: 0005_alert_delivery_integrity
"""

from alembic import op

revision = "0006_medication_adherence"
down_revision = "0005_alert_delivery_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE medication_schedules ADD COLUMN created_by uuid REFERENCES users(id);
    ALTER TABLE dose_events ADD COLUMN schedule_id uuid REFERENCES medication_schedules(id);
    ALTER TABLE dose_events ADD COLUMN schedule_state text NOT NULL DEFAULT 'active';
    ALTER TABLE dose_events ADD COLUMN reported_by uuid REFERENCES users(id);
    ALTER TABLE dose_events ADD COLUMN reported_note text;
    ALTER TABLE dose_events ADD CONSTRAINT ck_dose_events_schedule_state
      CHECK (schedule_state IN ('active', 'superseded'));
    ALTER TABLE dose_events DROP CONSTRAINT IF EXISTS dose_events_medication_id_scheduled_for_key;
    CREATE UNIQUE INDEX uq_dose_events_schedule_scheduled_for
      ON dose_events (schedule_id, scheduled_for) WHERE schedule_id IS NOT NULL;
    CREATE INDEX ix_dose_events_medication_scheduled_active
      ON dose_events (medication_id, scheduled_for) WHERE schedule_state = 'active';

    CREATE TABLE medication_reminder_deliveries (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      dose_event_id uuid NOT NULL REFERENCES dose_events(id),
      channel text NOT NULL, status text NOT NULL, attempts integer NOT NULL DEFAULT 0,
      last_error text, sent_at timestamptz,
      UNIQUE(dose_event_id, channel)
    );
    CREATE TABLE medication_concern_flags (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      dose_event_id uuid NOT NULL REFERENCES dose_events(id), patient_id uuid NOT NULL REFERENCES patients(id),
      reported_by uuid NOT NULL REFERENCES users(id), note text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_medication_concern_flags_patient_created
      ON medication_concern_flags (patient_id, created_at DESC);

    CREATE FUNCTION can_access_medication(target_medication uuid, requested_purpose text)
    RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
      SELECT EXISTS (
        SELECT 1 FROM public.medications m
        WHERE m.id = target_medication AND can_access_patient(m.patient_id, requested_purpose)
      )
    $$;

    DROP POLICY IF EXISTS medications_patient_policy ON medications;
    CREATE POLICY medications_read_policy ON medications FOR SELECT USING (
      can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY medications_physician_insert_policy ON medications FOR INSERT WITH CHECK (
      current_rpm_role() = 'physician'
      AND can_access_patient(patient_id, 'monitoring')
      AND EXISTS (SELECT 1 FROM physicians p WHERE p.id = prescriber_id AND p.user_id = current_rpm_user_id())
    );
    CREATE POLICY medications_physician_update_policy ON medications FOR UPDATE
      USING (current_rpm_role() = 'physician' AND can_access_patient(patient_id, 'monitoring'))
      WITH CHECK (
        current_rpm_role() = 'physician'
        AND can_access_patient(patient_id, 'monitoring')
        AND EXISTS (SELECT 1 FROM physicians p WHERE p.id = prescriber_id AND p.user_id = current_rpm_user_id())
      );

    ALTER TABLE medication_versions ENABLE ROW LEVEL SECURITY;
    ALTER TABLE medication_versions FORCE ROW LEVEL SECURITY;
    CREATE POLICY medication_versions_read_policy ON medication_versions FOR SELECT USING (
      can_access_medication(medication_id, 'monitoring')
    );
    CREATE POLICY medication_versions_physician_insert_policy ON medication_versions FOR INSERT WITH CHECK (
      current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring')
    );

    ALTER TABLE medication_schedules ENABLE ROW LEVEL SECURITY;
    ALTER TABLE medication_schedules FORCE ROW LEVEL SECURITY;
    CREATE POLICY medication_schedules_read_policy ON medication_schedules FOR SELECT USING (
      can_access_medication(medication_id, 'monitoring')
    );
    CREATE POLICY medication_schedules_physician_insert_policy ON medication_schedules FOR INSERT WITH CHECK (
      current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring')
    );
    CREATE POLICY medication_schedules_physician_update_policy ON medication_schedules FOR UPDATE
      USING (current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring'))
      WITH CHECK (current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring'));

    ALTER TABLE dose_events ENABLE ROW LEVEL SECURITY;
    ALTER TABLE dose_events FORCE ROW LEVEL SECURITY;
    CREATE POLICY dose_events_read_policy ON dose_events FOR SELECT USING (
      can_access_medication(medication_id, 'monitoring')
    );
    CREATE POLICY dose_events_patient_update_policy ON dose_events FOR UPDATE
      USING (
        (current_rpm_role() = 'patient' AND can_access_medication(medication_id, 'monitoring'))
        OR (current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring'))
        OR current_rpm_role() = 'worker'
      )
      WITH CHECK (
        (current_rpm_role() = 'patient' AND can_access_medication(medication_id, 'monitoring'))
        OR (current_rpm_role() = 'physician' AND can_access_medication(medication_id, 'monitoring'))
        OR current_rpm_role() = 'worker'
      );
    CREATE POLICY dose_events_worker_insert_policy ON dose_events FOR INSERT WITH CHECK (
      current_rpm_role() = 'worker'
    );

    ALTER TABLE medication_reminder_deliveries ENABLE ROW LEVEL SECURITY;
    ALTER TABLE medication_reminder_deliveries FORCE ROW LEVEL SECURITY;
    CREATE POLICY medication_reminder_deliveries_worker_policy ON medication_reminder_deliveries FOR ALL
      USING (current_rpm_role() = 'worker') WITH CHECK (current_rpm_role() = 'worker');

    ALTER TABLE medication_concern_flags ENABLE ROW LEVEL SECURITY;
    ALTER TABLE medication_concern_flags FORCE ROW LEVEL SECURITY;
    CREATE POLICY medication_concern_flags_read_policy ON medication_concern_flags FOR SELECT USING (
      can_access_patient(patient_id, 'monitoring')
    );
    CREATE POLICY medication_concern_flags_patient_insert_policy ON medication_concern_flags FOR INSERT
      WITH CHECK (
        current_rpm_role() = 'patient' AND can_access_patient(patient_id, 'monitoring')
        AND reported_by = current_rpm_user_id()
      );

    CREATE FUNCTION enforce_dose_event_write() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'dose events are retained for provenance';
      END IF;
      IF TG_OP = 'INSERT' THEN
        IF current_rpm_role() <> 'worker' THEN
          RAISE EXCEPTION 'dose events are generated only by a trusted worker';
        END IF;
        RETURN NEW;
      END IF;
      IF current_rpm_role() = 'worker' THEN
        RETURN NEW;
      END IF;
      IF current_rpm_role() = 'physician'
        AND OLD.medication_id IS NOT DISTINCT FROM NEW.medication_id
        AND OLD.scheduled_for IS NOT DISTINCT FROM NEW.scheduled_for
        AND OLD.schedule_id IS NOT DISTINCT FROM NEW.schedule_id
        AND OLD.status IS NOT DISTINCT FROM NEW.status
        AND OLD.recorded_at IS NOT DISTINCT FROM NEW.recorded_at
        AND OLD.reported_by IS NOT DISTINCT FROM NEW.reported_by
        AND OLD.reported_note IS NOT DISTINCT FROM NEW.reported_note
        AND OLD.schedule_state = 'active' AND NEW.schedule_state = 'superseded'
        AND OLD.status IN ('pending', 'unknown') AND OLD.scheduled_for > now() THEN
        RETURN NEW;
      END IF;
      IF current_rpm_role() <> 'patient' THEN
        RAISE EXCEPTION 'only a patient may self-report a dose';
      END IF;
      IF OLD.medication_id IS DISTINCT FROM NEW.medication_id
        OR OLD.scheduled_for IS DISTINCT FROM NEW.scheduled_for
        OR OLD.schedule_id IS DISTINCT FROM NEW.schedule_id
        OR OLD.schedule_state IS DISTINCT FROM NEW.schedule_state
        OR OLD.status NOT IN ('pending', 'unknown')
        OR NEW.status NOT IN ('taken', 'missed', 'skipped')
        OR NEW.reported_by IS DISTINCT FROM current_rpm_user_id()
        OR NEW.recorded_at IS NULL THEN
        RAISE EXCEPTION 'invalid dose self-report transition';
      END IF;
      RETURN NEW;
    END $$;
    CREATE TRIGGER dose_events_write_guard BEFORE INSERT OR UPDATE OR DELETE ON dose_events
      FOR EACH ROW EXECUTE FUNCTION enforce_dose_event_write();
    """)


def downgrade() -> None:
    raise RuntimeError(
        "Restore 0005_alert_delivery_integrity manually before downgrading this revision"
    )
