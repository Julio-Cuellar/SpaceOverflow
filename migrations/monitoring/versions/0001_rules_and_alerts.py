"""Reglas, alertas y reconocimientos de Monitoreo.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS monitoring")
    op.execute(
        """
        CREATE TABLE monitoring.rule (
          id                 uuid    PRIMARY KEY,
          key                text    NOT NULL UNIQUE,
          version            int     NOT NULL DEFAULT 1,
          kind               text    NOT NULL,
          parameter          text    NOT NULL,
          operator           text    NOT NULL,
          threshold          numeric NOT NULL,
          unit               text    NOT NULL,
          window_s           int     NOT NULL DEFAULT 0,
          severity           text    NOT NULL,
          source_requirement text    NOT NULL,
          source_document    text    NOT NULL,
          evidence_state     text    NOT NULL,
          hrp_hazard         text    NOT NULL,
          action_key         text    NOT NULL,
          active             boolean NOT NULL DEFAULT true,
          params             jsonb   NOT NULL DEFAULT '{}'::jsonb,
          supersedes         jsonb   NOT NULL DEFAULT '[]'::jsonb,
          CONSTRAINT rule_kind_chk CHECK (kind IN ('umbral', 'tendencia')),
          CONSTRAINT rule_severity_chk CHECK (severity IN ('atencion', 'alerta', 'critico')),
          CONSTRAINT rule_evidence_chk CHECK (evidence_state IN ('VERIFICADO', 'TB', 'DEMO'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE monitoring.alert (
          id              uuid        PRIMARY KEY,
          rule_id         uuid        NOT NULL REFERENCES monitoring.rule (id),
          habitat_id      uuid        NOT NULL,
          zone_id         uuid,
          crew_member_id  uuid,
          severity        text        NOT NULL,
          status          text        NOT NULL DEFAULT 'raised',
          cause_hint      text,
          evidence        jsonb       NOT NULL,
          dedupe_key      text        NOT NULL,
          clear_streak    int         NOT NULL DEFAULT 0,
          raised_at       timestamptz NOT NULL,
          acknowledged_at timestamptz,
          resolved_at     timestamptz,
          CONSTRAINT alert_severity_chk CHECK (severity IN ('atencion', 'alerta', 'critico')),
          CONSTRAINT alert_status_chk CHECK (status IN ('raised', 'acknowledged', 'resolved'))
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX alert_active_dedupe_uq ON monitoring.alert (dedupe_key) "
        "WHERE status <> 'resolved'"
    )
    op.execute(
        "CREATE INDEX alert_active_zone_idx ON monitoring.alert (habitat_id, zone_id) "
        "WHERE status <> 'resolved'"
    )
    op.execute(
        """
        CREATE TABLE monitoring.alert_ack (
          id             uuid        PRIMARY KEY,
          alert_id       uuid        NOT NULL REFERENCES monitoring.alert (id),
          crew_member_id uuid        NOT NULL,
          note           text,
          at             timestamptz NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monitoring.alert_ack")
    op.execute("DROP TABLE IF EXISTS monitoring.alert")
    op.execute("DROP TABLE IF EXISTS monitoring.rule")
