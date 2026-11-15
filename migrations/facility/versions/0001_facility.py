"""Floor plan, zones, active alerts per zone, incidents and their history.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS facility")
    op.execute(
        """
        CREATE TABLE facility.habitat (
          id                  uuid    PRIMARY KEY,
          code                text    NOT NULL UNIQUE,
          name                text    NOT NULL,
          kind                text    NOT NULL,
          p_total_nominal_kpa numeric NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE facility.zone (
          id                uuid        PRIMARY KEY,
          habitat_id        uuid        NOT NULL REFERENCES facility.habitat (id),
          code              text        NOT NULL,
          name              text        NOT NULL,
          kind              text        NOT NULL,
          deck              int         NOT NULL,
          layout            jsonb       NOT NULL,
          status            text        NOT NULL DEFAULT 'normal',
          status_changed_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE (habitat_id, code),
          CONSTRAINT zone_status_chk CHECK (status IN ('normal', 'attention', 'alert', 'critical'))
        )
        """
    )
    # Projection of the active Monitoring alerts per zone (no foreign key across schemas).
    op.execute(
        """
        CREATE TABLE facility.zone_alert (
          alert_id  uuid        PRIMARY KEY,
          zone_id   uuid        NOT NULL REFERENCES facility.zone (id),
          rule_key  text        NOT NULL,
          severity  text        NOT NULL,
          raised_at timestamptz NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE facility.incident (
          id               uuid        PRIMARY KEY,
          habitat_id       uuid        NOT NULL REFERENCES facility.habitat (id),
          zone_id          uuid        NOT NULL REFERENCES facility.zone (id),
          type_key         text        NOT NULL,
          source           text        NOT NULL,
          source_alert_id  uuid,
          reported_by      uuid,
          title            text        NOT NULL,
          description      text        NOT NULL,
          severity         text        NOT NULL,
          status           text        NOT NULL DEFAULT 'open',
          opened_at        timestamptz NOT NULL,
          acknowledged_at  timestamptz,
          resolved_at      timestamptz,
          values_normal_at timestamptz,
          CONSTRAINT incident_source_chk CHECK (source IN ('ALERT', 'MANUAL')),
          CONSTRAINT incident_status_chk CHECK (status IN ('open', 'acknowledged', 'resolved')),
          CONSTRAINT incident_severity_chk CHECK (severity IN ('attention', 'alert', 'critical'))
        )
        """
    )
    # A single open automatic ticket per zone.
    op.execute(
        "CREATE UNIQUE INDEX incident_one_open_auto_per_zone ON facility.incident (zone_id) "
        "WHERE source = 'ALERT' AND status <> 'resolved'"
    )
    op.execute("CREATE INDEX incident_opened_idx ON facility.incident (opened_at DESC, id DESC)")
    op.execute(
        """
        CREATE TABLE facility.incident_update (
          id          uuid        PRIMARY KEY,
          incident_id uuid        NOT NULL REFERENCES facility.incident (id),
          kind        text        NOT NULL,
          note        text,
          author_id   uuid,
          at          timestamptz NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX incident_update_incident_idx ON facility.incident_update (incident_id, at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS facility.incident_update")
    op.execute("DROP TABLE IF EXISTS facility.incident")
    op.execute("DROP TABLE IF EXISTS facility.zone_alert")
    op.execute("DROP TABLE IF EXISTS facility.zone")
    op.execute("DROP TABLE IF EXISTS facility.habitat")
