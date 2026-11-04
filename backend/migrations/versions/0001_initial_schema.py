"""Initial synthetic RPM schema with immutable clinical history.

Revision ID: 0001_initial_schema
Revises:
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
    CREATE TYPE user_role AS ENUM ('patient', 'physician', 'admin');
    CREATE TYPE observation_type AS ENUM ('glucose', 'blood_pressure', 'heart_rate', 'spo2');
    CREATE TYPE observation_source AS ENUM ('manual', 'device', 'imported');
    CREATE TYPE alert_severity AS ENUM ('informational', 'attention', 'urgent');
    CREATE TYPE alert_status AS ENUM ('open', 'notified', 'escalated', 'acknowledged', 'resolved');
    CREATE TYPE dose_status AS ENUM ('pending', 'unknown', 'taken', 'missed', 'skipped');
    CREATE TYPE meal_status AS ENUM ('pending', 'analysed', 'confirmed');
    CREATE TYPE artifact_kind AS ENUM ('meal_estimate', 'insight', 'summary');
    CREATE TYPE artifact_status AS ENUM ('draft', 'approved', 'rejected');

    CREATE TABLE users (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), email text NOT NULL UNIQUE, idp_subject text UNIQUE,
      role user_role NOT NULL, mfa_enabled boolean NOT NULL DEFAULT false, status text NOT NULL DEFAULT 'active',
      created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE patients (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL UNIQUE REFERENCES users(id),
      display_name text NOT NULL, date_of_birth date, sex text, timezone text NOT NULL DEFAULT 'Asia/Kolkata',
      diabetes_type text, has_hypertension boolean NOT NULL DEFAULT false, allergies jsonb NOT NULL DEFAULT '[]',
      comorbidities jsonb NOT NULL DEFAULT '[]', created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE physicians (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL UNIQUE REFERENCES users(id),
      registration_no text NOT NULL UNIQUE, specialty text, created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE consents (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id), purpose text NOT NULL,
      version text NOT NULL, granted_at timestamptz NOT NULL, revoked_at timestamptz,
      UNIQUE(patient_id, purpose, version, granted_at)
    );
    CREATE TABLE care_relationships (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      physician_id uuid NOT NULL REFERENCES physicians(id), consent_id uuid REFERENCES consents(id), status text NOT NULL,
      started_at timestamptz NOT NULL, ended_at timestamptz
    );
    CREATE TABLE observations (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      type observation_type NOT NULL, value_num numeric, components jsonb NOT NULL DEFAULT '{}', unit text NOT NULL,
      original_value numeric NOT NULL, original_unit text NOT NULL, measured_at timestamptz NOT NULL,
      recorded_at timestamptz NOT NULL DEFAULT now(), source observation_source NOT NULL, device_id uuid,
      entered_by uuid REFERENCES users(id), context jsonb NOT NULL DEFAULT '{}', quality_flag text,
      idempotency_key text, supersedes_id uuid REFERENCES observations(id),
      CHECK ((type = 'blood_pressure') OR value_num IS NOT NULL)
    );
    CREATE INDEX ix_observations_patient_type_measured_at ON observations(patient_id, type, measured_at DESC);
    CREATE TABLE monitoring_targets (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      type observation_type NOT NULL, context text NOT NULL DEFAULT 'default', low numeric, high numeric,
      set_by uuid REFERENCES users(id), version integer NOT NULL, effective_from timestamptz NOT NULL,
      UNIQUE(patient_id, type, context, version)
    );
    CREATE TABLE devices (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id), kind text NOT NULL,
      vendor text NOT NULL, serial text, status text NOT NULL, last_sync_at timestamptz
    );
    CREATE TABLE meals (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      eaten_at timestamptz NOT NULL, image_key text, status meal_status NOT NULL DEFAULT 'pending', note text
    );
    CREATE TABLE meal_items (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meal_id uuid NOT NULL REFERENCES meals(id), food_name text NOT NULL,
      food_code text, nutrient_source text, grams numeric, kcal numeric, carb_g numeric, protein_g numeric,
      fat_g numeric, fiber_g numeric, sugar_g numeric, sodium_mg numeric, confidence numeric,
      ai_estimated boolean NOT NULL DEFAULT false, user_corrected boolean NOT NULL DEFAULT false
    );
    CREATE TABLE medications (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id), name text NOT NULL,
      strength text, dose text, route text, frequency text, start_date date, end_date date,
      prescriber_id uuid REFERENCES physicians(id), instructions text, version integer NOT NULL DEFAULT 1
    );
    CREATE TABLE dose_events (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), medication_id uuid NOT NULL REFERENCES medications(id),
      scheduled_for timestamptz NOT NULL, status dose_status NOT NULL DEFAULT 'pending', recorded_at timestamptz,
      UNIQUE(medication_id, scheduled_for)
    );
    CREATE TABLE alert_rules (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text NOT NULL, version integer NOT NULL,
      definition jsonb NOT NULL, severity alert_severity NOT NULL, active boolean NOT NULL DEFAULT false,
      requires_clinician_approval boolean NOT NULL DEFAULT true, approved_by uuid REFERENCES users(id), approved_at timestamptz,
      UNIQUE(code, version)
    );
    CREATE TABLE alerts (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id),
      rule_code text NOT NULL, rule_version integer NOT NULL, observation_id uuid REFERENCES observations(id),
      severity alert_severity NOT NULL, status alert_status NOT NULL DEFAULT 'open', dedupe_key text NOT NULL,
      escalation_level integer NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(),
      acknowledged_by uuid REFERENCES users(id), acknowledged_at timestamptz, resolved_at timestamptz
    );
    CREATE TABLE notification_deliveries (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), alert_id uuid NOT NULL REFERENCES alerts(id), channel text NOT NULL,
      status text NOT NULL, attempts integer NOT NULL DEFAULT 0, last_error text, sent_at timestamptz
    );
    CREATE TABLE ai_artifacts (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), patient_id uuid NOT NULL REFERENCES patients(id), kind artifact_kind NOT NULL,
      content jsonb NOT NULL, model text, prompt_version text NOT NULL, input_refs jsonb NOT NULL, provider text NOT NULL,
      schema_version text NOT NULL, artifact_version integer NOT NULL, status artifact_status NOT NULL DEFAULT 'draft',
      reviewed_by uuid REFERENCES users(id), created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE messages (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), thread_id uuid NOT NULL, sender_id uuid NOT NULL REFERENCES users(id),
      recipient_id uuid NOT NULL REFERENCES users(id), body text NOT NULL, sent_at timestamptz NOT NULL DEFAULT now(), read_at timestamptz
    );
    CREATE TABLE audit_log (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor_id uuid REFERENCES users(id), actor_role user_role,
      action text NOT NULL, resource_type text NOT NULL, resource_id uuid, patient_id uuid REFERENCES patients(id),
      ip inet, at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE idempotency_records (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor_or_device_id uuid NOT NULL, operation text NOT NULL,
      key text NOT NULL, request_hash text NOT NULL, response_status integer, response_body jsonb, expires_at timestamptz,
      UNIQUE(actor_or_device_id, operation, key)
    );
    CREATE TABLE outbox_events (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), event_type text NOT NULL, payload_ref jsonb NOT NULL,
      created_at timestamptz NOT NULL DEFAULT now(), published_at timestamptz
    );
    CREATE TABLE job_attempts (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), outbox_event_id uuid REFERENCES outbox_events(id),
      attempts integer NOT NULL DEFAULT 0, next_retry_at timestamptz, dead_lettered_at timestamptz, last_error text
    );
    CREATE TABLE alert_events (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), alert_id uuid NOT NULL REFERENCES alerts(id), event_type text NOT NULL,
      severity alert_severity, actor_id uuid REFERENCES users(id), occurred_at timestamptz NOT NULL DEFAULT now(), details jsonb NOT NULL DEFAULT '{}'
    );
    CREATE TABLE medication_versions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), medication_id uuid NOT NULL REFERENCES medications(id),
      version integer NOT NULL, effective_from timestamptz NOT NULL, payload jsonb NOT NULL, UNIQUE(medication_id, version)
    );
    CREATE TABLE medication_schedules (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), medication_id uuid NOT NULL REFERENCES medications(id), timezone text NOT NULL,
      schedule jsonb NOT NULL, effective_from timestamptz NOT NULL, effective_to timestamptz
    );
    CREATE TABLE meal_item_versions (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), meal_item_id uuid NOT NULL REFERENCES meal_items(id),
      version integer NOT NULL, portion_low_g numeric, portion_high_g numeric, food_dataset_version text,
      missing_nutrient_flags jsonb NOT NULL DEFAULT '[]', payload jsonb NOT NULL, UNIQUE(meal_item_id, version)
    );
    CREATE TABLE artifact_reviews (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), artifact_id uuid NOT NULL REFERENCES ai_artifacts(id),
      artifact_version integer NOT NULL, reviewer_id uuid REFERENCES users(id), decision text NOT NULL, reviewed_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE identity_tokens (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL REFERENCES users(id), token_type text NOT NULL,
      token_hash text NOT NULL UNIQUE, revoked_at timestamptz, expires_at timestamptz NOT NULL
    );
    CREATE TABLE mfa_enrollments (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid NOT NULL UNIQUE REFERENCES users(id),
      encrypted_secret text NOT NULL, enrolled_at timestamptz NOT NULL DEFAULT now()
    );

    CREATE FUNCTION prevent_observation_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'observations are immutable; append a superseding record instead'; END; $$;
    CREATE TRIGGER observations_immutable BEFORE UPDATE OR DELETE ON observations
      FOR EACH ROW EXECUTE FUNCTION prevent_observation_mutation();
    CREATE FUNCTION prevent_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'audit_log is append-only'; END; $$;
    CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_log
      FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();

    DO $$ BEGIN CREATE ROLE rpm_runtime NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    REVOKE ALL ON audit_log FROM PUBLIC, rpm_runtime;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO rpm_runtime;
    GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rpm_runtime;
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit_log FROM rpm_runtime;
    """)


def downgrade() -> None:
    op.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
