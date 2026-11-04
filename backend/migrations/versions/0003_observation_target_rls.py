"""Protect monitoring targets with the Phase 2 RLS identity boundary.

Revision ID: 0003_observation_target_rls
Revises: 0002_identity_security
"""

from alembic import op

revision = "0003_observation_target_rls"
down_revision = "0002_identity_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    ALTER TABLE monitoring_targets ENABLE ROW LEVEL SECURITY;
    ALTER TABLE monitoring_targets FORCE ROW LEVEL SECURITY;
    CREATE POLICY monitoring_targets_patient_policy ON monitoring_targets FOR ALL
      USING (can_access_patient(patient_id, 'monitoring'))
      WITH CHECK (can_access_patient(patient_id, 'monitoring'));
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS monitoring_targets_patient_policy ON monitoring_targets;
    ALTER TABLE monitoring_targets DISABLE ROW LEVEL SECURITY;
    """)
