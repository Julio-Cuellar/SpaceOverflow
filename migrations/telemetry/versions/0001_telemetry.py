"""Sensores, lecturas particionadas por día, rollup por minuto y escenarios simulados.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS telemetry")
    op.execute(
        """
        CREATE TABLE telemetry.sensor (
          id              uuid    PRIMARY KEY,
          habitat_id      uuid    NOT NULL,
          zone_id         uuid,
          crew_member_id  uuid,
          domain          text    NOT NULL,
          metric          text    NOT NULL,
          unit            text    NOT NULL,
          sample_period_s int     NOT NULL,
          origin          text    NOT NULL,
          CONSTRAINT sensor_domain_chk CHECK (domain IN ('cuerpo', 'cabina', 'radiacion')),
          CONSTRAINT sensor_origin_chk CHECK (origin IN ('SIMULATED', 'REPLAY', 'REAL'))
        )
        """
    )
    op.execute("CREATE INDEX sensor_zone_metric_idx ON telemetry.sensor (zone_id, metric)")
    op.execute(
        """
        CREATE TABLE telemetry.reading (
          sensor_id uuid             NOT NULL REFERENCES telemetry.sensor (id),
          ts        timestamptz      NOT NULL,
          value     double precision NOT NULL,
          quality   text             NOT NULL DEFAULT 'ok',
          PRIMARY KEY (sensor_id, ts)
        ) PARTITION BY RANGE (ts)
        """
    )
    op.execute("CREATE TABLE telemetry.reading_default PARTITION OF telemetry.reading DEFAULT")
    op.execute("CREATE INDEX reading_ts_brin ON telemetry.reading USING brin (ts)")
    op.execute(
        """
        CREATE FUNCTION telemetry.ensure_reading_partition(day date) RETURNS void
        LANGUAGE plpgsql AS $$
        DECLARE
          part text := 'reading_' || to_char(day, 'YYYYMMDD');
        BEGIN
          EXECUTE format(
            'CREATE TABLE IF NOT EXISTS telemetry.%I PARTITION OF telemetry.reading '
            'FOR VALUES FROM (%L) TO (%L)',
            part,
            (day::timestamp AT TIME ZONE 'UTC'),
            ((day + 1)::timestamp AT TIME ZONE 'UTC')
          );
        END
        $$
        """
    )
    op.execute(
        """
        CREATE TABLE telemetry.reading_rollup_1m (
          sensor_id uuid             NOT NULL REFERENCES telemetry.sensor (id),
          bucket    timestamptz      NOT NULL,
          avg_v     double precision NOT NULL,
          min_v     double precision NOT NULL,
          max_v     double precision NOT NULL,
          n         int              NOT NULL,
          PRIMARY KEY (sensor_id, bucket)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE telemetry.scenario_run (
          id           uuid        PRIMARY KEY,
          habitat_id   uuid        NOT NULL,
          zone_id      uuid,
          scenario_key text        NOT NULL,
          state        text        NOT NULL,
          speed        numeric     NOT NULL DEFAULT 1,
          started_at   timestamptz NOT NULL,
          stopped_at   timestamptz,
          CONSTRAINT scenario_state_chk CHECK (state IN ('started', 'stopped'))
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telemetry.scenario_run")
    op.execute("DROP TABLE IF EXISTS telemetry.reading_rollup_1m")
    op.execute("DROP FUNCTION IF EXISTS telemetry.ensure_reading_partition(date)")
    op.execute("DROP TABLE IF EXISTS telemetry.reading")
    op.execute("DROP TABLE IF EXISTS telemetry.sensor")
